# 0014 · OpenAI, Anthropic und Google Gemini als optionale LLM-Anbieter außerhalb der EU

- **Status:** angenommen
- **Datum:** 2026-10-02

## Kontext

Der generische LLM-Adapter (ADR 0012) unterstützt fünf Anbieter. Mistral (Paris) verarbeitet in der EU, Ollama läuft selbst gehostet. OpenAI, Anthropic und Google (Gemini API) verarbeiten in den USA bzw. ohne garantierten EU-Standort. Google Gemini kam am 02.10.2026 auf Wunsch des Projektinhabers hinzu, weil die Gemini API ein kostenloses Kontingent hat. CLAUDE.md erlaubt Nicht-EU-Verarbeiter nur mit ADR, nur ohne personenbezogene Daten und nur, wenn sie per ENV gegen eine EU- oder selbst gehostete Option austauschbar sind.

## Entscheidung

- **OpenAI** (OpenAI, L.L.C.), **Anthropic** (Anthropic, PBC) und **Google Gemini** (Google LLC über die Gemini API, Vertragspartner im EWR: Google Ireland Ltd.) sind als **optionale** Anbieter zugelassen: `LLM_PROVIDER=openai`, `anthropic` bzw. `google`.
- **Standard in Produktion:** `mistral` (EU). Alternativ `ollama` auf eigener Hardware.
- Übertragen wird nur der Prompt aus `build_prompt`: PLZ, Ortsname, Radius, Zeitraum, Kategorien, dazu die Treffer der Web-Suche (öffentliche URLs, Titel, Snippets) während der Tool-Schleife. **Keine** Nutzer- oder Moderatordaten, keine Freitexte aus der App. Ein Snapshot-Test sichert, dass der Prompt nur diese Felder enthält.
- Der Wechsel ist reine Konfiguration (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`), ohne Deployment-Änderung am Code.

## Datenschutz

- Mangels personenbezogener Daten ist keine Drittlandübermittlung nach Art. 44 ff. DSGVO nötig. Vor einem produktiven Einsatz von OpenAI, Anthropic oder Gemini trotzdem: Auftragsverarbeitungsvertrag (DPA) abschließen, die Aufbewahrung der API-Daten beim Anbieter prüfen (Training mit API-Daten ist bei allen dreien standardmäßig aus, bei Gemini im EWR auch im kostenlosen Kontingent) und den Eintrag im Verarbeiterverzeichnis auf „aktiv“ setzen.
- Gemini: Für Nutzer im EWR gelten die Datenregeln der kostenpflichtigen Dienste auch für das kostenlose Kontingent (keine Nutzung zur Produktverbesserung, Data Processing Addendum). Eine Verarbeitung in der EU wäre nur über Google Cloud (Vertex AI) mit EU-Region möglich; dafür fehlt bisher ein Adapter-Zweig (`GoogleCloudProvider`, Dienstkonto statt API-Schlüssel).
- Zurückschalten auf die EU: `LLM_PROVIDER=mistral` (oder `ollama`) und Neustart von API und Worker.
- Einträge: [Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md), [Verarbeitungsverzeichnis Nr. 10](../30-privacy/verarbeitungsverzeichnis.md).

## Konsequenzen

- Moderierende können bei schwacher Trefferqualität einen anderen Anbieter testen, ohne dass Code geändert wird.
- Unterschiedliche Modelle liefern unterschiedliche Qualität. Die strenge Validierung (`EventDraftV1`, Quellenpflicht, Duplikat- und Umkreisprüfung) gilt für alle gleich, Funde landen immer nur als Entwurf.
- Kosten fallen je Anbieter an; `AI_SEARCH_DAILY_LIMIT` und `AI_SEARCH_MAX_TOOL_CALLS` begrenzen sie. Die Token-Zahl jedes Jobs steht im Job-Protokoll.

## Verworfene Alternativen

- **Nur EU-Anbieter:** sicherer, nimmt aber die Möglichkeit, die Qualität zu vergleichen. Die Option bleibt durch den Standard `mistral` erhalten.
