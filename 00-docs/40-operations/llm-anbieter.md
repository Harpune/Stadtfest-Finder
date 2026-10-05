# LLM-Anbieter für die KI-Suche einrichten

## Zweck

Das Sprachmodell der KI-Suche per PLZ (R10, Flow C). Ein generischer Adapter (Pydantic AI, [ADR 0012](../25-adr/0012-llm-adapter-pydantic-ai.md)) spricht den per ENV gewählten Anbieter an. Standard in Produktion ist **Mistral (EU)**. OpenAI, Anthropic und Google Gemini sind optional ([ADR 0014](../25-adr/0014-llm-anbieter-ausserhalb-eu.md)), Ollama läuft selbst gehostet.

## Voraussetzungen

- Eine eingerichtete Web-Suche ([web-suche.md](web-suche.md)); ohne sie liefert das Modell keine belegbaren Quellen.
- Je nach Anbieter:
  - **Mistral:** Konto auf https://console.mistral.ai. Zum Testen reicht der kostenlose Tarif „Experiment“ (Telefonnummer nötig; den Tarif im Workspace aktivieren, sonst antwortet die API mit `429` und `x-ratelimit-limit-req-minute: 0`; am 05.10.2026 15 Anfragen pro Minute, `mistral-large-latest` enthalten). Dort dürfen Eingaben zum Training genutzt werden. Unsere Prompts enthalten keine personenbezogenen Daten, für den Betrieb trotzdem den kostenpflichtigen Tarif „Scale“ (Zahlungsart hinterlegen) wählen, bei dem das nicht gilt.
  - **OpenAI:** Konto auf https://platform.openai.com mit Guthaben bzw. Zahlungsart.
  - **Anthropic:** Konto auf https://console.anthropic.com mit Guthaben bzw. Zahlungsart.
  - **Google Gemini:** Google-Konto mit Zugang zu Google AI Studio (https://aistudio.google.com). Der kostenlose Tarif reicht nur zum Ausprobieren: Er erlaubt je Modell ca. 20 Anfragen pro Tag (gemessen am 05.10.2026 mit `gemini-3.8-flash`, aktuelle Werte unter *AI Studio → Usage & limits*). Eine KI-Suche braucht bis zu `AI_SEARCH_MAX_TOOL_CALLS` + 2 Anfragen (eine pro Web-Suche plus Start und Ergebnis), also bei Standardwerten etwa 2 Suchen pro Tag. Für den Betrieb die Abrechnung im zugehörigen Google-Cloud-Projekt aktivieren.
  - **Ollama:** ein Rechner bzw. Container mit Ollama (https://ollama.com) und genug RAM/GPU für ein Modell mit Tool-Calling (z. B. `qwen3`, `llama3.1`).
- Zugriff auf die lokale `.env` bzw. die Secrets in Komodo (Produktion).

## Schritte

1. **AV-Vertrag prüfen** (nur Cloud-Anbieter): Data Processing Addendum des Anbieters abschließen bzw. akzeptieren. Prüfen, dass API-Daten nicht zum Training genutzt werden. Den Status im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) eintragen.
   - Gemini: Für Nutzer im EWR gelten laut den „Gemini API Additional Terms of Service“ die Datenregeln der kostenpflichtigen Dienste auch für das kostenlose Kontingent: Eingaben und Antworten werden nicht zur Produktverbesserung genutzt, es gilt Googles Data Processing Addendum. Das gilt, weil der Projektinhaber seinen Sitz im EWR hat. Die Verarbeitung findet nicht garantiert in der EU statt (Nicht-EU-Verarbeiter, ADR 0014).
2. **API-Schlüssel anlegen:**
   - Mistral: *API Keys → Create new key*, Name `stadtfest-prod` (für Entwicklung `stadtfest-dev`).
   - OpenAI: *API keys → Create new secret key*, eigenes Projekt `stadtfest`, Berechtigung nur für die Modelle.
   - Anthropic: *API Keys → Create Key* in einem eigenen Workspace `stadtfest`.
   - Google Gemini: in AI Studio *Get API key → Create API key*, dabei ein eigenes Google-Cloud-Projekt `stadtfest` wählen bzw. anlegen. Den Schlüssel in der Cloud Console unter *APIs & Services → Credentials* auf die „Generative Language API“ beschränken.
   - Ollama: kein Schlüssel. Modell laden: `ollama pull <modell>`.
3. **Ausgabelimit setzen:** Im Dashboard des Anbieters ein monatliches Budget bzw. Limit für das Projekt bzw. den Workspace einstellen (Gemini: Budget-Alarm unter *Billing → Budgets & alerts* im Cloud-Projekt; im kostenlosen Tarif begrenzen die Rate-Limits). Die App begrenzt zusätzlich selbst: `AI_SEARCH_DAILY_LIMIT` (Suchen je Moderator und Tag), `AI_SEARCH_MAX_TOOL_CALLS` (Web-Suchen je Job), `AI_SEARCH_TIMEOUT_S`.
4. **Modell wählen:** Es muss Tool-Calling und strukturierte Ausgabe können. Beispiele: `mistral-large-latest`, `gpt-4.1-mini`, `claude-sonnet-4-5`, für Gemini ein aktuelles `gemini-…-flash`- oder `-pro`-Modell (Liste: https://ai.google.dev/gemini-api/docs/models). Den genauen Namen aus der Modellliste des Anbieters übernehmen.
5. **Secrets hinterlegen** – lokal in `.env` (siehe `.env.example`), in Produktion als Komodo-Secret. **Niemals ins Repo.**
   ```bash
   LLM_PROVIDER=mistral          # mistral | openai | anthropic | google | ollama
   LLM_MODEL=mistral-large-latest
   LLM_API_KEY=<schlüssel>       # leer bei ollama
   LLM_BASE_URL=                 # nur bei ollama oder eigenem Endpunkt, z. B. http://ollama:11434/v1
   ```
   Beispiel Gemini:
   ```bash
   LLM_PROVIDER=google
   LLM_MODEL=<gemini-modell aus der Modellliste>
   LLM_API_KEY=<schlüssel aus AI Studio>
   ```
6. **API und Worker neu starten.** Beide lesen die Einstellungen beim Start; ein fehlender Schlüssel oder ein unbekannter Anbieter beendet den Start mit einer klaren Meldung.

## Prüfung

- Der Worker startet ohne Fehler (`python -m stadtfest.bootstrap.worker`).
- In der App als Moderator: „Suchen“ → eigene PLZ → „Suche starten“. Nach einigen Sekunden bis Minuten zeigt die Leiste „{n} neue Entwürfe aus der Suche für {PLZ}“ oder „Keine neuen Feste gefunden“.
- `GET /v1/mod/ai-searches/{jobId}` liefert `status: completed`. Bei `failed` sagt `errorCode` den Grund: `llm_unavailable` (Schlüssel, Kontingent, Modellname), `search_unavailable` (Web-Suche), `timeout`.
- Das Worker-Log nennt bei Fehlern nur Job-ID und Fehlercode, keine Inhalte. Zähler, Suchanfragen und Token-Zahl stehen im Job-Protokoll (`ai_search_job.log`).
- Im Dashboard des Anbieters erscheinen die Anfragen und Kosten.

## Prompt-Versionen und Auswertung

- Der Prompt der KI-Suche ist versioniert (`backend/src/stadtfest/application/ai_ingestion/prompts/`, [R10b](../10-specs/R10b-ki-suche-qualitaet.md)). Auswahl per `AI_SEARCH_PROMPT_VERSION` (Standard `v3`), lokal zum Ausprobieren auch `AI_SEARCH_PROMPT_FILE`.
- Vergleich mit dem eingestellten Anbieter, ohne etwas zu speichern:
  ```bash
  make ai-eval ZIPS="73430 89073" PROMPTS=v1,v2 OUT=ai-eval.md
  ```
  Jeder Lauf kostet Anfragen (bei kostenlosen Tarifen das Tageskontingent im Blick behalten). Für aussagekräftige Ergebnisse lokal Nominatim nutzen (`GEOCODING_PROVIDER=nominatim`), sonst lassen sich echte Adressen nicht verorten.

## Rollback

- **Gemini überlastet oder Kontingent erschöpft** (`llm_unavailable`): Der Adapter wiederholt `429`/`503` bis zu fünfmal mit wachsender Pause (ca. 30 s). Das Worker-Log zeigt dann `Retrying … 503 UNAVAILABLE` (Google überlastet, vorübergehend) bzw. `429 RESOURCE_EXHAUSTED` (Kontingent). Beim Tageskontingent hilft nur warten (Reset um Mitternacht US-Pazifikzeit), ein anderes Gemini-Modell (eigenes Kontingent je Modell), Abrechnung aktivieren oder ein anderer Anbieter.
- **Zurück auf die EU:** `LLM_PROVIDER=mistral` (bzw. `ollama`) mit passendem `LLM_MODEL` und `LLM_API_KEY` setzen, API und Worker neu starten.
- **KI-Suche vorübergehend stoppen:** `AI_SEARCH_DAILY_LIMIT=0` setzen und neu starten; neue Suchen enden dann mit `429`. Hängende Jobs markiert der Wächter (alle 10 Minuten) nach der doppelten `AI_SEARCH_TIMEOUT_S` als `timeout`.
- **Schlüssel kompromittiert:** im Dashboard des Anbieters widerrufen, neuen Schlüssel anlegen, Secret ersetzen, neu starten.
- In Entwicklung und Tests: `LLM_PROVIDER=fake` liefert drei feste Funde ohne externen Aufruf.
