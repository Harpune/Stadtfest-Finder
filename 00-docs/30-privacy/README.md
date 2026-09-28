# Datenschutz (DSGVO)

Dieser Ordner enthält die Datenschutz-Dokumentation. Sie wird **im selben PR** gepflegt, der personenbezogene Daten einführt oder ändert (CLAUDE.md „Privacy“, Regel 7 in [`10-specs/README.md`](../10-specs/README.md#querschnittsregeln-für-alle-inkremente)).

| Dokument | Inhalt |
|---|---|
| [verarbeitungsverzeichnis.md](verarbeitungsverzeichnis.md) | Verzeichnis der Verarbeitungstätigkeiten (VVT, Art. 30) |
| [toms.md](toms.md) | Technische und organisatorische Maßnahmen (Art. 32) |
| [loeschkonzept.md](loeschkonzept.md) | Aufbewahrungsfristen und Löschwege (Art. 17), inkl. Kontolöschung |
| [auftragsverarbeiter.md](auftragsverarbeiter.md) | Eingesetzte Dienstleister mit Standort und ADR |

**Grundsätze:**
- Datenminimierung: Gespeichert werden nur die hier aufgeführten Felder.
- Keine personenbezogenen Daten in Logs, LLM-Prompts, Web-Suchen oder Push-Payloads.
- Jede Entität mit Personenbezug hat eine Frist und einen Löschweg, beides ist durch Tests abgedeckt.
