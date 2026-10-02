# 0012 · Generischer LLM-Adapter mit Pydantic AI

- **Status:** angenommen
- **Datum:** 2026-10-02

## Kontext

Die KI-Suche per PLZ (R10, Flow C) braucht ein Sprachmodell mit Tool-Calling (Web-Suche) und strukturierter Ausgabe (festes Fest-Schema). CLAUDE.md verlangt **einen** generischen Adapter hinter dem LLM-Port. Der Anbieter (Mistral, OpenAI, Anthropic, Google Gemini, Ollama) wird nur per ENV gewählt, ohne Codeänderung. Zur Wahl standen LiteLLM und Pydantic AI.

## Entscheidung

- **Pydantic AI** (`pydantic-ai-slim` mit den Extras `mistral`, `openai`, `anthropic`, `google`) implementiert den Port `EventFinder` in `adapters/outbound/llm/pydantic_ai.py`.
- `build_model(LlmConfig)` baut das Modell nur aus der Konfiguration:

  | `LLM_PROVIDER` | Modellklasse | Schlüssel | `LLM_BASE_URL` |
  |---|---|---|---|
  | `mistral` | `MistralModel` | Pflicht | optional |
  | `openai` | `OpenAIChatModel` | Pflicht | optional (OpenAI-kompatible Endpunkte) |
  | `anthropic` | `AnthropicModel` | Pflicht | optional |
  | `google` | `GoogleModel` (Gemini API) | Pflicht | optional |
  | `ollama` | `OllamaModel` | – | Standard `http://localhost:11434/v1` |
  | `fake` | kein Modell, `FakeEventFinder` mit drei festen Funden | – | nur `ENV=dev` oder `test` |

- Ein `Agent` erhält das Tool `web_search`, das über den Web-Such-Port (ADR 0013) läuft. Die Zahl der Tool-Aufrufe begrenzt `AI_SEARCH_MAX_TOOL_CALLS` (`UsageLimits`), die Laufzeit `AI_SEARCH_TIMEOUT_S`.
- **Ausgabe in zwei Stufen:** Das Modell liefert eine tolerante Liste (`_LooseDraft`, alle Felder optional). Danach prüft der Adapter jeden Eintrag einzeln gegen das versionierte Schema `EventDraftV1`. Ungültige Einträge werden gezählt und ohne Inhalt geloggt; ein fehlerhafter Fund verwirft so nicht die ganze Antwort. Das strenge Schema mit verschachtelten `$defs` scheiterte beim Erzeugen des Ausgabeschemas.
- Der Start prüft die Einstellungen (fail fast): unbekannter Anbieter, fehlender Schlüssel oder `fake` in Produktion beenden den Start.

## Konsequenzen

- Der Anbieterwechsel ist reine Konfiguration. Ein Unit-Test baut die Modelle aller Anbieter.
- Tests rufen nie echte Anbieter auf: `FunctionModel` von Pydantic AI spielt die aufgezeichnete Antwort `tests/fixtures/llm/finds_73430.json` ab, im Dev-Betrieb läuft der Fake.
- Pydantic AI bringt Pydantic als Laufzeitbasis mit, die das Backend ohnehin nutzt. Die Anbieter-SDKs kommen nur über die gewählten Extras.
- Anbieterspezifische Eigenheiten (z. B. eingebaute Web-Suche einzelner Anbieter) werden bewusst nicht genutzt, damit alle Anbieter gleich arbeiten.

## Verworfene Alternativen

- **LiteLLM:** breite Anbieterabdeckung über eine OpenAI-kompatible Schnittstelle, aber Tool-Schleife, Usage-Limits und Validierung gegen Pydantic-Modelle hätten wir selbst bauen müssen. Größere Abhängigkeit mit Proxy-Funktionen, die wir nicht brauchen.
- **Je ein eigener Adapter pro Anbieter:** widerspricht CLAUDE.md („one generic adapter“) und vervielfacht Tests.
