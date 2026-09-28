# 0002 · Hexagonale Architektur und Bounded Contexts

- **Status:** angenommen
- **Datum:** 2026-09-28

## Kontext

REST-API, Worker und MCP-Server greifen auf dieselbe Geschäftslogik zu. Externe Systeme (LLM-Anbieter, Geocoding, Push, Objektspeicher) sollen per Konfiguration austauschbar sein.

## Entscheidung

- **Schichten:** `domain` (reines Python) ← `application` (Use Cases, Ports) ← `adapters` ← `bootstrap` (Composition Root).
- **Bounded Contexts:** `events`, `collections`, `ai_ingestion`, `moderation`. Ein fünfter Kontext `notifications` ist vorgeschlagen (R11).
- **Adapter-Pakete heißen `adapters/inbound/` und `adapters/outbound/`** statt `adapters/in/` und `adapters/out/`. `in` ist ein reserviertes Python-Keyword, `stadtfest.adapters.in.rest` wäre nicht importierbar. CLAUDE.md ist entsprechend angepasst.
- **Einstiegspunkte** liegen in `bootstrap/`, weil nur dort Adapter verdrahtet werden:
  - API: `uvicorn stadtfest.bootstrap.app:create_app --factory`
  - Worker: `python -m stadtfest.bootstrap.worker`
  - MCP: ab R15
- **Durchsetzung per Tooling:** `import-linter` (in `make lint`) prüft
  - die Schichtenreihenfolge,
  - dass `domain` nichts aus FastAPI, SQLAlchemy, Pydantic, Redis, arq, httpx, structlog oder `generated` importiert,
  - dass `application` keine Frameworks und keine generierten API-Modelle importiert.

## Konsequenzen

- Use Cases bekommen Ports (Python-Protokolle) injiziert. Tests nutzen Fake-Adapter.
- Router mappen generierte API-Modelle (`generated/`) auf Use-Case-Ein- und -Ausgaben. Die API-Modelle sickern nicht in die Application-Schicht.

## Verworfene Alternativen

- `adapters/in_/` bzw. `adapters/input/`: `inbound`/`outbound` ist in der hexagonalen Literatur verbreiteter.
