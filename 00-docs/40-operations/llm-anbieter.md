# LLM-Anbieter für die KI-Suche einrichten

## Zweck

Das Sprachmodell der KI-Suche per PLZ (R10, Flow C). Ein generischer Adapter (Pydantic AI, [ADR 0012](../25-adr/0012-llm-adapter-pydantic-ai.md)) spricht den per ENV gewählten Anbieter an. Standard in Produktion ist **Mistral (EU)**. OpenAI und Anthropic sind optional ([ADR 0014](../25-adr/0014-llm-anbieter-ausserhalb-eu.md)), Ollama läuft selbst gehostet.

## Voraussetzungen

- Eine eingerichtete Web-Suche ([web-suche.md](web-suche.md)); ohne sie liefert das Modell keine belegbaren Quellen.
- Je nach Anbieter:
  - **Mistral:** Konto auf https://console.mistral.ai mit hinterlegter Zahlungsart (Workspace mit Abrechnung).
  - **OpenAI:** Konto auf https://platform.openai.com mit Guthaben bzw. Zahlungsart.
  - **Anthropic:** Konto auf https://console.anthropic.com mit Guthaben bzw. Zahlungsart.
  - **Ollama:** ein Rechner bzw. Container mit Ollama (https://ollama.com) und genug RAM/GPU für ein Modell mit Tool-Calling (z. B. `qwen3`, `llama3.1`).
- Zugriff auf die lokale `.env` bzw. die Secrets in Komodo (Produktion).

## Schritte

1. **AV-Vertrag prüfen** (nur Cloud-Anbieter): Data Processing Addendum des Anbieters abschließen bzw. akzeptieren. Prüfen, dass API-Daten nicht zum Training genutzt werden. Den Status im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) eintragen.
2. **API-Schlüssel anlegen:**
   - Mistral: *API Keys → Create new key*, Name `stadtfest-prod` (für Entwicklung `stadtfest-dev`).
   - OpenAI: *API keys → Create new secret key*, eigenes Projekt `stadtfest`, Berechtigung nur für die Modelle.
   - Anthropic: *API Keys → Create Key* in einem eigenen Workspace `stadtfest`.
   - Ollama: kein Schlüssel. Modell laden: `ollama pull <modell>`.
3. **Ausgabelimit setzen:** Im Dashboard des Anbieters ein monatliches Budget bzw. Limit für das Projekt bzw. den Workspace einstellen. Die App begrenzt zusätzlich selbst: `AI_SEARCH_DAILY_LIMIT` (Suchen je Moderator und Tag), `AI_SEARCH_MAX_TOOL_CALLS` (Web-Suchen je Job), `AI_SEARCH_TIMEOUT_S`.
4. **Modell wählen:** Es muss Tool-Calling und strukturierte Ausgabe können. Beispiele: `mistral-large-latest`, `gpt-4.1-mini`, `claude-sonnet-4-5`. Den genauen Namen aus der Modellliste des Anbieters übernehmen.
5. **Secrets hinterlegen** – lokal in `.env` (siehe `.env.example`), in Produktion als Komodo-Secret. **Niemals ins Repo.**
   ```bash
   LLM_PROVIDER=mistral          # mistral | openai | anthropic | ollama
   LLM_MODEL=mistral-large-latest
   LLM_API_KEY=<schlüssel>       # leer bei ollama
   LLM_BASE_URL=                 # nur bei ollama oder eigenem Endpunkt, z. B. http://ollama:11434/v1
   ```
6. **API und Worker neu starten.** Beide lesen die Einstellungen beim Start; ein fehlender Schlüssel oder ein unbekannter Anbieter beendet den Start mit einer klaren Meldung.

## Prüfung

- Der Worker startet ohne Fehler (`python -m stadtfest.bootstrap.worker`).
- In der App als Moderator: „Suchen“ → eigene PLZ → „Suche starten“. Nach einigen Sekunden bis Minuten zeigt die Leiste „{n} neue Entwürfe aus der Suche für {PLZ}“ oder „Keine neuen Feste gefunden“.
- `GET /v1/mod/ai-searches/{jobId}` liefert `status: completed`. Bei `failed` sagt `errorCode` den Grund: `llm_unavailable` (Schlüssel, Kontingent, Modellname), `search_unavailable` (Web-Suche), `timeout`.
- Das Worker-Log nennt bei Fehlern nur Job-ID und Fehlercode, keine Inhalte. Zähler, Suchanfragen und Token-Zahl stehen im Job-Protokoll (`ai_search_job.log`).
- Im Dashboard des Anbieters erscheinen die Anfragen und Kosten.

## Rollback

- **Zurück auf die EU:** `LLM_PROVIDER=mistral` (bzw. `ollama`) mit passendem `LLM_MODEL` und `LLM_API_KEY` setzen, API und Worker neu starten.
- **KI-Suche vorübergehend stoppen:** `AI_SEARCH_DAILY_LIMIT=0` setzen und neu starten; neue Suchen enden dann mit `429`. Hängende Jobs markiert der Wächter (alle 10 Minuten) nach der doppelten `AI_SEARCH_TIMEOUT_S` als `timeout`.
- **Schlüssel kompromittiert:** im Dashboard des Anbieters widerrufen, neuen Schlüssel anlegen, Secret ersetzen, neu starten.
- In Entwicklung und Tests: `LLM_PROVIDER=fake` liefert drei feste Funde ohne externen Aufruf.
