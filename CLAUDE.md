# CLAUDE.md – Stadtfest-Finder

Mobile app to discover local festivals and events (Stadtfeste, Volksfeste, Kirmes,
Weihnachtsmärkte, Märkte) in Germany by ZIP code and radius. Guests search publicly,
registered users manage favorites/lists/invitations, moderators run AI-assisted event
searches and publish reviewed drafts. External AI clients access data via an MCP server.

Architecture: @00-docs/20-architecture/system-architecture.md
Decisions: @00-docs/25-adr/

## Tech stack

| Area | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + GeoAlchemy2, Alembic, uv |
| MCP server | FastMCP (standalone package), Streamable HTTP, OAuth via the same IdP |
| Worker / queue | arq on Redis |
| Database | PostgreSQL + PostGIS |
| Cache | Redis |
| Object storage | S3-compatible, EU-hosted (SeaweedFS locally, see ADR 0007) – event images |
| Auth | OIDC/OAuth2 + PKCE; Zitadel Cloud (EU region) in production, Keycloak locally |
| AI | Own LLM port with one generic adapter (Pydantic AI, ADR 0012); provider selected via env: Mistral (EU), OpenAI, Anthropic, Google Gemini, Ollama (local) |
| Web search | Web search API used as an LLM tool (provider: see ADR) |
| Geocoding | Self-hosted Nominatim (Germany extract, EU) via geocoding port; app never calls it directly, only via `/v1/geocode*` |
| Push | Push port, provider selected via env: Expo Push Service or direct APNs / FCM |
| Mobile | React Native + Expo (TypeScript), expo-router, TanStack Query, MapLibre, Storybook for React Native |
| Tests | pytest, Testcontainers, Schemathesis · Jest + RN Testing Library · Maestro (E2E) |
| CI/CD | GitHub Actions → GHCR → Komodo on home server (EU) |

## Commands

Run everything from the repo root. Always use these instead of ad-hoc commands.

```bash
make dev          # start local stack (docker compose) + backend with reload
make seed         # load synthetic test data into local DB
make gen          # regenerate code from api/openapi.yaml (backend models + mobile client)
make fmt          # format all code
make lint         # lint + type check (ruff, mypy, gts, tsc, spectral)
make test         # unit + integration tests
make test-e2e     # Maestro flows against local stack
make check        # everything CI runs – must pass before you finish a task
```

## Repository layout

```
00-docs/
  10-specs/            requirements, user stories
  15-design/           UI/UX, design system
  20-architecture/     C4 diagrams, flows
  25-adr/              architecture decision records (NNNN-title.md)
  30-privacy/          GDPR: records of processing (VVT), TOMs, deletion concept
  40-operations/       runbooks, step-by-step guides for external services
api/
  openapi.yaml         single source of truth for the REST API
backend/
  src/stadtfest/
    domain/<context>/          entities, value objects, domain services (pure Python)
    application/<context>/     use cases, ports (in/out)
    adapters/inbound/rest/     FastAPI routers
    adapters/inbound/mcp/      MCP tools
    adapters/inbound/worker/   arq job handlers
    adapters/outbound/<tech>/  persistence, storage, queue, cache, llm, geocoding, search, push, auth
    generated/                 generated from openapi.yaml – DO NOT EDIT
    bootstrap/                 composition root, DI wiring, settings, entry points (app, worker)
  migrations/                  Alembic
  tests/{unit,integration,contract}/
mobile/
  src/app/                     expo-router screens
  src/features/<feature>/      feature modules
  src/components/              shared UI components (component library)
  src/api/generated/           generated API client – DO NOT EDIT
  .maestro/                    E2E flows
infra/
  compose.yaml                 production stack (deployed via Komodo)
  compose.dev.yaml             local dependencies
seed/                          synthetic seed data + loader
.github/workflows/
```

## Roles and auth

| Role | Token | Can |
|---|---|---|
| Guest | none | map, list, search, filter |
| `user` | JWT | + favorites, share, invitations with accept/decline, shared lists, notifications |
| `moderator` | JWT | + maintain events of own region, maintain categories, start AI search by ZIP, review/publish drafts |

- The app logs in directly at the IdP (Authorization Code + PKCE). The backend never handles
  passwords; it only validates JWTs against the IdP's JWKS and reads roles from claims.
- Public endpoints must work without a token. Authorization checks (role, region scope)
  live in use cases, not in routers, so REST, MCP and worker enforce the same rules.
- The MCP server uses OAuth against the same IdP.

## Library documentation (Context7)

- Use the **Context7 MCP server** whenever possible before writing or changing code that
  uses a third-party library or framework (FastAPI, Pydantic, SQLAlchemy, Alembic, arq,
  FastMCP, Expo, React Native, TanStack Query, MapLibre, LiteLLM/Pydantic AI, Storybook, Maestro, …).
- Workflow: resolve the library ID first, then query the docs for the specific topic.
  Use the version pinned in `pyproject.toml` / `package.json` when Context7 offers it.
- Prefer Context7 over memory for APIs, configuration options and migration guides –
  library APIs change faster than training data.
- If Context7 is unavailable or has no entry for a library, fall back to the official
  documentation and say so in the PR description.

## Code conventions

- All code, identifiers, comments, commit messages and PR descriptions in **English**.
  Documentation in `00-docs/` is written in **German**.
- Follow the Google Style Guides (https://google.github.io/styleguide/):
  Python Style Guide for the backend, TypeScript Style Guide for mobile.
  Style is enforced by tooling (ruff with Google docstring convention, mypy strict, gts).
  If tooling and prose disagree, tooling wins.
- Type everything. No `Any` / `any` without a comment explaining why.
- Small, focused functions; docstrings on all public modules, classes and functions.

## API-first

- `api/openapi.yaml` (OpenAPI 3.1) is the contract. **Interface changes are made only there.**
- Workflow for any API change:
  1. Edit `api/openapi.yaml`.
  2. `make gen` to regenerate backend models and the mobile client.
  3. Implement or adapt routers/use cases.
  4. `make check` – contract tests verify the running app matches the spec.
- Never hand-edit files under `generated/`. Never change the API by adding FastAPI routes
  or parameters that are not in the spec.
- Breaking changes require a new API version and an ADR. CI checks with `oasdiff`.
- The MCP server does not follow the OpenAPI spec; its tools call application use cases directly.

## Backend architecture (hexagonal + DDD)

- Bounded contexts:
  - `events` – events, categories, regions, PostGIS radius search
  - `collections` – favorites, lists, invitations
  - `ai_ingestion` – AI search jobs, event drafts
  - `moderation` – review, publish (region-scoped)
- Dependency rule: `adapters → application → domain`. Never the other way round.
- `domain/` is pure Python: no imports from FastAPI, SQLAlchemy, Pydantic, Redis, httpx.
- Business logic lives in domain and application only. Adapters translate and delegate.
- Every external system is accessed through an outbound port (interface in `application/`)
  with an adapter in `adapters/outbound/`. (Packages are named `inbound`/`outbound` because
  `in` is a Python keyword, see ADR 0002.) Layer rules are enforced by `import-linter`. This keeps LLM providers, geocoding etc. swappable.
- REST API, MCP server and worker share the same use cases – no logic duplication.
  (The architecture diagram calls this the "Service-Schicht".)
- Contexts communicate via application services or domain events, not by reaching into
  each other's persistence.
- Database changes only via Alembic migrations. Never edit a migration that is on `main`.

## Core flows

Flow letters match the architecture diagram.

- **A – Guest search:** app → `GET` REST (no token) → `events` use case → PostGIS radius
  query → list + map. Cached (see Caching).
- **B – Login:** app ↔ IdP (OIDC + PKCE) → access token → API validates JWT via JWKS.
- **C – AI search by ZIP (async):**
  1. Moderator starts search in the app → API creates a search job (`ai_ingestion`) and
     enqueues it in arq. The request returns immediately.
  2. Worker picks up the job → geocoding (ZIP → coordinates/radius).
  3. LLM port with web search tool → structured JSON matching the fixed event schema.
  4. Validate with Pydantic; invalid items are discarded and logged (without content).
  5. Store as **draft** – never published directly.
  6. Moderator reviews and publishes (`moderation`) → event becomes public, search caches
     are invalidated; notification via push if relevant.
- **D – MCP:** external AI client (e.g. Claude Desktop) → MCP server (Streamable HTTP,
  OAuth) → same use cases → database.

## AI ingestion

- The LLM is accessed only through the LLM port, implemented by **one generic adapter**
  (no provider-specific adapters for OpenAI, Anthropic, Google Gemini, Mistral, Ollama).
- Provider and model are selected via environment only – no code change to switch:
  ```bash
  LLM_PROVIDER=mistral          # mistral | openai | anthropic | google | ollama
  LLM_MODEL=mistral-large-latest
  LLM_API_KEY=...               # not needed for ollama
  LLM_BASE_URL=                 # optional, e.g. http://ollama:11434
  ```
- Settings are validated at startup (`bootstrap/`); an unknown provider or missing key
  fails fast. Document every variable in `.env.example`.
- The provider must support tool calling and structured output; the web search tool and
  the event schema are passed provider-independently.
- Output schema for an event draft (fixed, versioned in code):
  name, date_from, date_to, place, address, coordinates, category, source_url, description.
- Every draft must carry `source_url`. Drafts without a verifiable source are rejected.
- Prompts contain only ZIP code, radius, time range and categories (see Privacy).

## Push notifications

- Sent only through the push port. Two adapters, selected via env – no code change to switch:
  ```bash
  PUSH_PROVIDER=expo            # expo | direct | disabled
  EXPO_ACCESS_TOKEN=...         # expo only
  APNS_KEY_ID=... APNS_TEAM_ID=... APNS_KEY_PATH=...   # direct only
  FCM_PROJECT_ID=... FCM_CREDENTIALS_PATH=...          # direct only
  ```
- `expo`: Expo Push Service → APNs / FCM. Handles retries and receipts.
- `direct`: backend sends to APNs / FCM itself; one processor fewer outside the EU.
- `disabled`: no-op adapter (default for tests and local dev).
- Settings are validated at startup; missing credentials for the selected provider fail fast.
- Payloads contain IDs only, regardless of provider.

## MCP tools

| Tool | Access | Use case |
|---|---|---|
| `search_events(zip_code, radius_km, date_from, date_to)` | public / user | `events` search |
| `get_event(event_id)` | public / user | `events` detail |
| `start_ai_search(zip_code)` | `moderator` only | `ai_ingestion` create job |

Tools are thin adapters: parse input, call the use case, map the result. No business logic.

## Caching

- Cache in Redis via a cache port; never cache inside domain code.
- Cache: public guest geo searches (TTL 5 min), geocoding results ZIP → coordinates (TTL 30 days),
  category/region lists (TTL 1 h).
- Invalidate affected search caches when an event is published, updated or unpublished.
- Never cache user-specific or personal data.

## Privacy (GDPR / DSGVO) – hard rules

- Data minimization: store only fields listed in `00-docs/30-privacy/`. New personal data
  fields require an update of the records of processing (VVT) in the same PR.
- **Never log personal data** (emails, names, tokens, IPs, user free text). Log user IDs only
  where necessary.
- **Never send personal data to LLM providers or web search.** AI prompts may contain
  only public event data, ZIP codes and moderator-independent parameters.
- Push payloads contain no personal content – only IDs; the app fetches details via API.
- Every entity with personal data needs a deletion path (account deletion, Art. 17) and a
  defined retention period, covered by tests.
- All infrastructure and processors must be EU-hosted, except where an ADR documents
  the legal basis. Accepted non-EU processors (each documented in an ADR):
  Expo Push Service (optional, `PUSH_PROVIDER=expo`), APNs / FCM (unavoidable for push),
  OpenAI, Anthropic, Google Gemini, the web search provider (if non-EU).
- Non-EU processors must be switchable via env to an EU or self-hosted option
  (push: `direct`/`disabled`, LLM: `mistral`/`ollama`). Personal data never reaches them.
  Default LLM provider in production: Mistral (EU) or Ollama (self-hosted).

## Mobile

- Targets: iOS and Android only. Web is not a target; do not add web-specific code,
  `.web.tsx` files or web-only dependencies.
- Screens in `src/app/`, logic in `src/features/`, reusable UI only from `src/components/`.
- Build UI from the shared component library in `src/components/`. Every shared component
  has a Storybook story (Storybook for React Native) covering its main states
  (default, loading, empty, error, disabled). New or changed components are not done
  without an updated story.
- Every interactive element gets a stable `testID` so Maestro flows and integration tests
  can target it. Do not change existing `testID`s without updating the flows.
- API access only through the generated client + TanStack Query hooks.
- Auth only via OIDC + PKCE against the IdP; store tokens in secure storage only.
- Map: MapLibre with OSM-based vector tiles from MapTiler Cloud (ADR 0009, key via
  `EXPO_PUBLIC_MAPTILER_KEY`; without a key an offline background style is used); no Google Maps SDK.
- Push: register the token matching `PUSH_PROVIDER` via the API (Expo push token for
  `expo`, native device token via `getDevicePushTokenAsync` for `direct`); handle
  invitation and reminder notifications by ID and fetch details from the API.

## Testing

- New use cases: unit tests in `tests/unit` with fake adapters for all ports.
- Adapters: integration tests with Testcontainers (PostGIS, Redis, SeaweedFS).
- API: Schemathesis contract tests against `api/openapi.yaml`.
- LLM calls: never hit real providers in tests; use recorded fixtures or the fake adapter.
  Same for web search, geocoding (Nominatim) and push.
- MCP tools: test role checks (e.g. `start_ai_search` rejected for non-moderators).
- Mobile: Jest + RN Testing Library for components, Maestro for critical user flows
  (guest search, login, favorites, moderator publish).

## Git & CI/CD

- Never commit to `main`. Work on `feature/<short-description>` or `fix/<short-description>`,
  merge via PR only.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- **Commit, push and merge policy for Claude:**
  - Claude may commit and push on `feature/*` and `fix/*` branches without asking.
  - **Commit** after each coherent step of an increment (e.g. a finished user story, or a
    self-contained layer such as spec + generated code, migration, use case + tests, screen).
    Each commit must leave the branch green for the affected area (`make lint` + relevant
    tests); keep commits atomic and reference the increment/story, e.g.
    `feat(R03-US7): add filter sheet with month grid`.
  - **Push** when a feature is complete (at the latest when a user story or an increment from
    `00-docs/10-specs/` is done and `make check` passes locally), then open or update the PR
    to `main`.
  - Claude may **merge a PR into `main` only when the complete pipeline is green** (all
    required checks passed, none pending or skipped due to failure). If the pipeline is
    red, fix it on the branch and push again – never merge red, never bypass branch
    protection, never force-push, never enable auto-merge unless explicitly asked.
- PR pipeline: format check, lint + type check, OpenAPI lint + `oasdiff`, generated-code
  drift check, tests, security scan (Trivy, CodeQL), AI review (claude-code-action).
- Only `main` builds Docker images → pushed to GHCR, tagged with commit SHA and SemVer.
- Deployment: Komodo on the home server (located in the EU) deploys the stack from `infra/compose.yaml`
  (API, MCP server, worker, PostgreSQL/PostGIS, Redis, object storage).
  See `00-docs/40-operations/deployment-komodo.md`.
- Mobile builds are not Docker images; they run via EAS Build (separate workflow).

## External services

Any setup outside this repo (Zitadel, GHCR, Komodo, DNS, Expo push / APNs / FCM credentials,
LLM API keys, web search API key, …) needs a step-by-step guide in `00-docs/40-operations/`
using the template `00-docs/40-operations/_template.md`: purpose, prerequisites, numbered steps,
verification, rollback. Write the guide in the same PR that introduces the dependency.

Secrets never go into the repo. Use `.env` locally (see `.env.example`) and GitHub/Komodo
secrets in CI/production.

## Definition of done

- [ ] `make check` passes
- [ ] API changes made in `api/openapi.yaml` and code regenerated
- [ ] Tests added or updated for the change
- [ ] Privacy docs updated if personal data is touched
- [ ] ADR added for architectural decisions and new non-EU processors
- [ ] Guides in `00-docs/40-operations/` added for new external setup
- [ ] Architecture diagram updated if containers or flows change

## When unsure

Ask before: adding a new dependency, adding a new external service, changing the data model
of personal data, or deviating from the architecture. Prefer a short question over a guess.
