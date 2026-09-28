# Verzeichnis der Verarbeitungstätigkeiten (VVT)

> Stand R02: Es werden noch keine personenbezogenen Daten **gespeichert**. Die Suche verarbeitet Standortdaten nur flüchtig. Pro Verarbeitung eine Zeile, das Nutzerkonto folgt in R05.

| Nr. | Verarbeitung | Zweck | Betroffene | Datenkategorien (Felder) | Rechtsgrundlage | Empfänger / Auftragsverarbeiter | Drittland | Frist | Löschweg | Inkrement |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Festsuche mit Standort | Feste im Umkreis anzeigen, Entfernungen berechnen | Gäste, Nutzer | Position (`lat`, `lon`) als Anfrageparameter, Suchtext `q` | Art. 6 (1) f (Bereitstellung der angefragten Suche) | keine; eigener Server (EU) | nein | nicht gespeichert; Cache-Schlüssel nur als Hash über auf ~1 km gerundete Koordinaten, TTL 5 min | entfällt | R02 |
| 2 | Orts-/PLZ-Suche und Reverse-Geocoding | Wohnort bzw. Ortsname zum Standort ermitteln | Gäste, Nutzer | Suchtext; Position, vor der Abfrage auf ~100 m gerundet | Art. 6 (1) f | selbst gehostetes Nominatim (EU, ADR 0006) | nein | nicht gespeichert; Cache nur für gerundete Raster-Koordinaten bzw. gehashten Suchtext, TTL 30 Tage | entfällt | R02 |
| 3 | Rate-Limit Geocoding | Schutz vor Missbrauch | Gäste, Nutzer | gehashte IP-Adresse | Art. 6 (1) f | keine | nein | 2 Sekunden (Redis-TTL) | automatischer Ablauf | R02 |

## Nicht gespeicherte, nur verarbeitete Daten

| Daten | Wo | Behandlung |
|---|---|---|
| IP-Adressen | API (Transport) | nicht geloggt (Uvicorn-Access-Log aus, eigener Request-Log ohne IP), nur gehasht und 2 s lang für Rate-Limits (Nr. 3) |
| Query-Parameter (z. B. `lat`, `lon`, `q`) | API | aus Logs entfernt (`bootstrap/logging.py`, Test `test_logging.py`) |
| Tokens | API | nie geloggt |
