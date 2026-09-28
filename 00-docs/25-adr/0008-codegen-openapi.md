# 0008 · Codegen aus der OpenAPI-Spezifikation

- **Status:** angenommen
- **Datum:** 2026-09-28

## Kontext

`api/openapi.yaml` ist der Vertrag (API-first). Aus ihm entstehen die Pydantic-Modelle des Backends sowie der Client und die TanStack-Query-Hooks der App. Die Werkzeuge wurden per Context7-Dokumentation verglichen.

## Entscheidung

**Backend:** `datamodel-code-generator` (Konfiguration in `backend/pyproject.toml`)
- erzeugt Pydantic-v2-Modelle nach `backend/src/stadtfest/generated/models.py`
- snake_case-Feldnamen mit camelCase-Aliasen, Formatierung mit ruff

**Mobile:** `openapi-typescript` + `openapi-fetch` + `openapi-react-query`
- generiert wird nur die Typdatei `mobile/src/api/generated/schema.d.ts`
- Laufzeit: ein generischer, typsicherer Fetch-Client (ca. 6 kB) mit Middleware für Auth und Token-Refresh (R05)
- Hooks per `$api.useQuery("get", "/v1/events", …)`

**Drift-Check:** `make gen` und danach `git diff --exit-code` in CI.

## Bewertung Mobile

| Kriterium | Orval | openapi-typescript-Stack | hey-api |
|---|---|---|---|
| Generierter Code | groß (Hooks, Modelle) | eine `.d.ts` | mittel |
| Auth/Refresh | eigener Mutator, Fehlertypisierung umständlich | eingebaute Middleware | Interceptors |
| Mocks | MSW, in React Native nur mit Polyfills | keine | teilweise |
| OpenAPI 3.1 | ja | ja, ausdrücklich | ja |
| Reife | stabil | stabil | vor 1.0, häufige Breaking Changes |

Den Ausschlag gaben die minimale Laufzeit, die passende Middleware für den Token-Refresh und der kleine generierte Diff. Orvals Hauptvorteil (Mocks) trägt unter React Native kaum.

## Konsequenzen

- Es gibt keine benannten Hooks pro Operation. Die App kapselt häufige Aufrufe in Feature-Hooks (`useEventSearch` usw.).
- Query-Keys sind `[method, path, init]`. Invalidierungen erfolgen über den Pfad.
