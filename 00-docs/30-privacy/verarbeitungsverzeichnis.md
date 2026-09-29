# Verzeichnis der Verarbeitungstätigkeiten (VVT)

> Stand R05: Gespeichert wird das Nutzerkonto (Nr. 5, nur IdP-Subject und Name). Die Suche verarbeitet Standortdaten nur flüchtig. Pro Verarbeitung eine Zeile.

| Nr. | Verarbeitung | Zweck | Betroffene | Datenkategorien (Felder) | Rechtsgrundlage | Empfänger / Auftragsverarbeiter | Drittland | Frist | Löschweg | Inkrement |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Festsuche im Kartenausschnitt | Feste im sichtbaren Kartenausschnitt anzeigen | Gäste, Nutzer | Kartenausschnitt (`bbox`, auf ein Raster erweitert), Suchtext `q`; **keine** Position (Entfernungen rechnet das Gerät, ab 29.09.2026) | Art. 6 (1) f (Bereitstellung der angefragten Suche) | keine; eigener Server (EU) | nein | nicht gespeichert; Cache-Schlüssel nur als Hash über auf ~1 km gerundete Koordinaten, TTL 5 min | entfällt | R02 |
| 2 | Orts-/PLZ-Suche und Reverse-Geocoding | Wohnort bzw. Ortsname zum Standort ermitteln | Gäste, Nutzer | Suchtext; Position, vor der Abfrage auf ~100 m gerundet | Art. 6 (1) f | selbst gehostetes Nominatim (EU, ADR 0006) | nein | nicht gespeichert; Cache nur für gerundete Raster-Koordinaten bzw. gehashten Suchtext, TTL 30 Tage | entfällt | R02 |
| 4 | Kartenkacheln laden | Karte darstellen | Gäste, Nutzer | IP-Adresse, Kachelkoordinaten des betrachteten Ausschnitts (kein Standort, keine Nutzer-ID) | Art. 6 (1) f | MapTiler AG (ADR 0009) | Schweiz (Angemessenheitsbeschluss) | laut DPA von MapTiler | entfällt (keine eigene Speicherung) | R03 |
| 3 | Rate-Limit Geocoding | Schutz vor Missbrauch | Gäste, Nutzer | gehashte IP-Adresse | Art. 6 (1) f | keine | nein | 2 Sekunden (Redis-TTL) | automatischer Ablauf | R02 |
| 5 | Nutzerkonto | Anmeldung, Zuordnung von Favoriten, Listen und Einladungen, Anzeige des Namens | Nutzer, Moderatoren | Tabelle `app_user`: interne ID, IdP-Subject (`idp_subject`), Vorname, Nachname, Zeitstempel. **Keine** E-Mail-Adresse, keine Anbieterliste (E-08). Rollen und Region stehen nur im Token und werden nicht gespeichert. | Art. 6 (1) b (Nutzungsvertrag) | keine; eigener Server (EU) | nein | bis zur Kontolöschung | `DELETE /v1/me` → Use Case `DeleteAccount` ([Löschkonzept](loeschkonzept.md)) | R05 |
| 6 | Anmeldung beim IdP | Authentifizierung (Apple, Google, E-Mail), Rollenvergabe | Nutzer, Moderatoren | beim IdP: E-Mail, Name, Anmeldedaten, Rollen, Region-Metadatum (Moderatoren); ggf. Verknüpfung mit Apple/Google | Art. 6 (1) b | Zitadel Cloud (EU-Region, ADR 0003); lokal Keycloak | nein | bis zur Kontolöschung | IdP-Admin-Port löscht den Nutzer beim IdP (ADR 0010), Retry per Job | R05 |

## Nicht gespeicherte, nur verarbeitete Daten

| Daten | Wo | Behandlung |
|---|---|---|
| IP-Adressen | API (Transport) | nicht geloggt (Uvicorn-Access-Log aus, eigener Request-Log ohne IP), nur gehasht und 2 s lang für Rate-Limits (Nr. 3) |
| Query-Parameter (z. B. `lat`, `lon`, `q`) | API | aus Logs entfernt (`bootstrap/logging.py`, Test `test_logging.py`) |
| Tokens | API | nie geloggt (weder `Authorization`-Header noch Token-Inhalt; Test `test_me_api.py::test_tokens_and_names_are_never_logged`) |
| Tokens (App) | Gerät (`expo-secure-store`, Keychain/Keystore) | Access-, Refresh- und ID-Token; nie in AsyncStorage; beim Abmelden und bei der Kontolöschung gelöscht, der Refresh-Token wird beim IdP widerrufen |
| E-Mail-Adresse (App) | Gerät (aus dem ID-Token) | nur angezeigt (Drawer, Konto-Seite), nie an das Backend gesendet |
| Eigener Standort (App) | Gerät | verlässt das Gerät nicht; nur für den blauen Punkt, die Startansicht und Entfernungen (auf dem Gerät berechnet). Der Ortsname in der Liste („um {Ort}“) stammt aus der auf ~1 km gerundeten **Kartenmitte** über `/v1/geocode/reverse` |
| Letzter Kartenausschnitt (App) | Gerät (AsyncStorage) | nur **ohne** Standortfreigabe gespeichert (dann ist er nicht die eigene Position), auf 2 Nachkommastellen gerundet; Startansicht beim nächsten Öffnen (R03-US1) |
| Letztes Suchergebnis (App) | Gerät (AsyncStorage) | nur öffentliche Festdaten und Zeitpunkt, keine Position; Offline-Lesen (R03-US8) |
