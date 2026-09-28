# CI auf GitHub einrichten

## Zweck

Die PR-Pipeline (`.github/workflows/ci.yml`, `codeql.yml`, `ai-review.yml`) und der Image-Build auf `main` (`release.yml`) laufen auf GitHub Actions. Eingeführt mit [R01](../10-specs/R01-fundament.md). Merges nach `main` nur mit grüner Pipeline (CLAUDE.md).

## Voraussetzungen

- Admin-Rechte am Repository `Harpune/Stadtfest-Finder`
- Für das KI-Review: ein Anthropic-API-Key

## Schritte

1. **Actions aktivieren:** *Settings → Actions → General* → „Allow all actions“ (bzw. die genutzten Actions freigeben). *Workflow permissions:* „Read repository contents“ genügt, die Workflows fordern ihre Rechte selbst an.
2. **KI-Review (optional):** *Settings → Secrets and variables → Actions → New repository secret* `ANTHROPIC_API_KEY`. Ohne Secret überspringt `ai-review.yml` den Lauf und bleibt grün.
3. **Code scanning (CodeQL):** Der Workflow `codeql.yml` analysiert immer. Bei Funden schlägt er fehl und listet sie im Job-Log auf.
   - **Öffentliches Repository** (aktueller Stand): Die Ergebnisse werden automatisch nach *Security → Code scanning* hochgeladen, es ist nichts zu tun.
   - Für **private Repositories** braucht der Upload das kostenpflichtige GitHub Code Security. Ohne das bleibt der Upload aus.
   - Mit Code Security: *Settings → Code security* → Code scanning aktivieren („Default setup“ **nicht** zusätzlich einschalten) und die Repository-Variable `CODE_SCANNING_ENABLED=true` setzen (*Settings → Secrets and variables → Actions → Variables*).
4. **Branch-Schutz für `main`:** *Settings → Branches → Add rule* (bzw. Ruleset)
   - „Require a pull request before merging“
   - „Require status checks to pass“ mit den Checks:
     - `Backend (format, lint, types, architecture, tests)`
     - `OpenAPI (lint, breaking changes)`
     - `Mobile (lint, types, tests)`
     - `Generated code is up to date`
     - `Security scan (Trivy)`
     - `CodeQL (python)`, `CodeQL (javascript-typescript)`, `CodeQL (actions)`
   - „Do not allow bypassing“ und kein Force-Push
5. **GHCR:** Nach dem ersten Lauf von `release.yml` erscheint das Paket `stadtfest-backend` unter *Packages*. Sichtbarkeit bleibt privat. Komodo erhält später einen Read-Token (R16).

## Prüfung

- Ein PR zeigt alle genannten Checks. Ein absichtlich falsch formatierter Commit lässt „Backend“ bzw. „Mobile“ rot werden.
- Nach einem Merge auf `main` gibt es ein Image `ghcr.io/harpune/stadtfest-backend:sha-<commit>`.

## Rollback

- Workflows lassen sich unter *Actions → Workflow → Disable workflow* abschalten.
- Den Branch-Schutz nur im Notfall lockern und danach sofort wiederherstellen.
