# Verzeichnis der Verarbeitungstätigkeiten (VVT)

> Stand R03: Es werden noch keine personenbezogenen Daten **gespeichert**. Die Suche verarbeitet Standortdaten nur flüchtig. Pro Verarbeitung eine Zeile, das Nutzerkonto folgt in R05.

| Nr. | Verarbeitung | Zweck | Betroffene | Datenkategorien (Felder) | Rechtsgrundlage | Empfänger / Auftragsverarbeiter | Drittland | Frist | Löschweg | Inkrement |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Festsuche im Kartenausschnitt | Feste im sichtbaren Kartenausschnitt anzeigen | Gäste, Nutzer | Kartenausschnitt (`bbox`, auf ein Raster erweitert), Suchtext `q`; **keine** Position (Entfernungen rechnet das Gerät, ab 29.09.2026) | Art. 6 (1) f (Bereitstellung der angefragten Suche) | keine; eigener Server (EU) | nein | nicht gespeichert; Cache-Schlüssel nur als Hash über auf ~1 km gerundete Koordinaten, TTL 5 min | entfällt | R02 |
| 2 | Orts-/PLZ-Suche und Reverse-Geocoding | Wohnort bzw. Ortsname zum Standort ermitteln | Gäste, Nutzer | Suchtext; Position, vor der Abfrage auf ~100 m gerundet | Art. 6 (1) f | selbst gehostetes Nominatim (EU, ADR 0006) | nein | nicht gespeichert; Cache nur für gerundete Raster-Koordinaten bzw. gehashten Suchtext, TTL 30 Tage | entfällt | R02 |
| 4 | Kartenkacheln laden | Karte darstellen | Gäste, Nutzer | IP-Adresse, Kachelkoordinaten des betrachteten Ausschnitts (kein Standort, keine Nutzer-ID) | Art. 6 (1) f | MapTiler AG (ADR 0009) | Schweiz (Angemessenheitsbeschluss) | laut DPA von MapTiler | entfällt (keine eigene Speicherung) | R03 |
| 3 | Rate-Limit Geocoding | Schutz vor Missbrauch | Gäste, Nutzer | gehashte IP-Adresse | Art. 6 (1) f | keine | nein | 2 Sekunden (Redis-TTL) | automatischer Ablauf | R02 |

## Nicht gespeicherte, nur verarbeitete Daten

| Daten | Wo | Behandlung |
|---|---|---|
| IP-Adressen | API (Transport) | nicht geloggt (Uvicorn-Access-Log aus, eigener Request-Log ohne IP), nur gehasht und 2 s lang für Rate-Limits (Nr. 3) |
| Query-Parameter (z. B. `lat`, `lon`, `q`) | API | aus Logs entfernt (`bootstrap/logging.py`, Test `test_logging.py`) |
| Tokens | API | nie geloggt |
| Eigener Standort (App) | Gerät | verlässt das Gerät nicht; nur für den blauen Punkt, die Startansicht und Entfernungen (auf dem Gerät berechnet). Der Ortsname in der Liste („um {Ort}“) stammt aus der auf ~1 km gerundeten **Kartenmitte** über `/v1/geocode/reverse` |
| Letzter Kartenausschnitt (App) | Gerät (AsyncStorage) | nur **ohne** Standortfreigabe gespeichert (dann ist er nicht die eigene Position), auf 2 Nachkommastellen gerundet; Startansicht beim nächsten Öffnen (R03-US1) |
| Letztes Suchergebnis (App) | Gerät (AsyncStorage) | nur öffentliche Festdaten und Zeitpunkt, keine Position; Offline-Lesen (R03-US8) |
