# Verzeichnis der Verarbeitungstätigkeiten (VVT)

> Stand R01: noch keine personenbezogenen Daten gespeichert. Einträge folgen ab R02 (Suche mit Standort) und R05 (Nutzerkonto). Pro Verarbeitung eine Zeile.

| Nr. | Verarbeitung | Zweck | Betroffene | Datenkategorien (Felder) | Rechtsgrundlage | Empfänger / Auftragsverarbeiter | Drittland | Frist | Löschweg | Inkrement |
|---|---|---|---|---|---|---|---|---|---|---|
| – | – | – | – | – | – | – | – | – | – | – |

## Nicht gespeicherte, nur verarbeitete Daten

| Daten | Wo | Behandlung |
|---|---|---|
| IP-Adressen | API (Transport) | nicht geloggt (Uvicorn-Access-Log aus, eigener Request-Log ohne IP), ab R02 nur flüchtig für Rate-Limits |
| Query-Parameter (z. B. `lat`, `lon`, `q`) | API | aus Logs entfernt (`bootstrap/logging.py`, Test `test_logging.py`) |
| Tokens | API | nie geloggt |
