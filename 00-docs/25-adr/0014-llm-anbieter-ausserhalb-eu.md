# 0014 · OpenAI und Anthropic als optionale LLM-Anbieter außerhalb der EU

- **Status:** angenommen
- **Datum:** 2026-10-02

## Kontext

Der generische LLM-Adapter (ADR 0012) unterstützt vier Anbieter. Mistral (Paris) verarbeitet in der EU, Ollama läuft selbst gehostet. OpenAI und Anthropic sitzen in den USA. CLAUDE.md erlaubt Nicht-EU-Verarbeiter nur mit ADR, nur ohne personenbezogene Daten und nur, wenn sie per ENV gegen eine EU- oder selbst gehostete Option austauschbar sind.

## Entscheidung

- **OpenAI** (OpenAI, L.L.C.) und **Anthropic** (Anthropic, PBC) sind als **optionale** Anbieter zugelassen: `LLM_PROVIDER=openai` bzw. `anthropic`.
- **Standard in Produktion:** `mistral` (EU). Alternativ `ollama` auf eigener Hardware.
- Übertragen wird nur der Prompt aus `build_prompt`: PLZ, Ortsname, Radius, Zeitraum, Kategorien, dazu die Treffer der Web-Suche (öffentliche URLs, Titel, Snippets) während der Tool-Schleife. **Keine** Nutzer- oder Moderatordaten, keine Freitexte aus der App. Ein Snapshot-Test sichert, dass der Prompt nur diese Felder enthält.
- Der Wechsel ist reine Konfiguration (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`), ohne Deployment-Änderung am Code.

## Datenschutz

- Mangels personenbezogener Daten ist keine Drittlandübermittlung nach Art. 44 ff. DSGVO nötig. Vor einem produktiven Einsatz von OpenAI oder Anthropic trotzdem: Auftragsverarbeitungsvertrag (DPA) abschließen, die Aufbewahrung der API-Daten beim Anbieter prüfen (Training mit API-Daten ist bei beiden standardmäßig aus) und den Eintrag im Verarbeiterverzeichnis auf „aktiv“ setzen.
- Zurückschalten auf die EU: `LLM_PROVIDER=mistral` (oder `ollama`) und Neustart von API und Worker.
- Einträge: [Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md), [Verarbeitungsverzeichnis Nr. 10](../30-privacy/verarbeitungsverzeichnis.md).

## Konsequenzen

- Moderierende können bei schwacher Trefferqualität einen anderen Anbieter testen, ohne dass Code geändert wird.
- Unterschiedliche Modelle liefern unterschiedliche Qualität. Die strenge Validierung (`EventDraftV1`, Quellenpflicht, Duplikat- und Regionsprüfung) gilt für alle gleich, Funde landen immer nur als Entwurf.
- Kosten fallen je Anbieter an; `AI_SEARCH_DAILY_LIMIT` und `AI_SEARCH_MAX_TOOL_CALLS` begrenzen sie. Die Token-Zahl jedes Jobs steht im Job-Protokoll.

## Verworfene Alternativen

- **Nur EU-Anbieter:** sicherer, nimmt aber die Möglichkeit, die Qualität zu vergleichen. Die Option bleibt durch den Standard `mistral` erhalten.
