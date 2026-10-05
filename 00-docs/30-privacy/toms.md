# Technische und organisatorische Maßnahmen (TOMs)

> Stand R01. Wird mit jedem Inkrement ergänzt.

| Bereich | Maßnahme | Umsetzung | Seit |
|---|---|---|---|
| Vertraulichkeit | Keine Passwörter im Backend | Anmeldung ausschließlich beim IdP (OIDC + PKCE, ADR 0003) | R01 |
| Vertraulichkeit | Keine personenbezogenen Daten in Logs | Log-Filter entfernt Tokens, IPs, Koordinaten, Suchtexte, Namen, E-Mails; Test `tests/unit/test_logging.py` | R01 |
| Vertraulichkeit | Secrets nicht im Repository | `.env` (git-ignoriert), GitHub-/Komodo-Secrets; Trivy-Secret-Scan in CI | R01 |
| Vertraulichkeit | Keine Fehlerdetails an Clients | Einheitliches Fehlerformat, `500` ohne Details | R01 |
| Integrität | Code-Review und automatische Prüfungen | PR-Pflicht, grüne Pipeline (Lint, Tests, CodeQL, Trivy) vor Merge | R01 |
| Integrität | Architekturregeln | import-linter verhindert Framework-Abhängigkeiten in `domain` | R01 |
| Verfügbarkeit | Health-/Readiness-Probes | `/v1/health/live`, `/v1/health/ready` | R01 |
| Verfügbarkeit | Backups | folgt in R16 | – |
| Belastbarkeit | Rate-Limits | Geocoding 5 Anfragen/s je Client (IP gehasht, 2 s TTL) | R02 |
| Vertraulichkeit | Standortdaten minimiert | Keine Speicherung von Nutzerpositionen; Reverse-Geocoding auf ~100 m gerundet; Cache-Schlüssel nur über gerundete Werte, gehasht; Geocoding selbst gehostet | R02 |
| Standort | Kern in der EU | Eigener Server (EU), Zitadel EU-Region; Nicht-EU-Dienste nur per ADR und per ENV abschaltbar | R01 |
| Vertraulichkeit | Bildmetadaten entfernt | Der Worker kopiert nur Pixel (EXIF, XMP, IPTC, ICC inkl. GPS fallen weg), Originale werden gelöscht; Test mit GPS-EXIF in `test_pillow_processor.py` | R08 |
| Vertraulichkeit | Objektspeicher abgeschottet | Upload nur über signierte URLs (10 min, nur für einen Schlüssel; Größe beim Anhängen, Typ im Worker geprüft); anonym lesbar nur `public/`; Schlüssel enthalten nur IDs ([ADR 0011](../25-adr/0011-bildauslieferung.md)) | R08 |
| Integrität | Dateityp am Inhalt geprüft | Magic Bytes statt Dateiname; nur JPEG, PNG, WebP; Schutz vor Dekompressionsbomben (max. 50 Mio. Pixel) | R08 |
| Vertraulichkeit | Keine personenbezogenen Daten an KI- und Such-Anbieter | Prompt nur aus PLZ, Ortsnamen (gesuchter Ort und Orte im Umkreis), Radius, Zeitraum, Kategorien: versionierte Vorlagen mit Erlaubnisliste der Platzhalter, die beim Start geprüft wird (R10b), Snapshot-Test; EU-Anbieter Mistral als Standard, Nicht-EU-Anbieter nur per ENV ([ADR 0012–0014](../25-adr/0012-llm-adapter-pydantic-ai.md)) | R10 |
| Integrität | KI-Funde nie direkt öffentlich | Funde werden nur Entwürfe; Schema-Validierung je Fund, Quellenpflicht (URL aus den Suchergebnissen des Jobs, erreichbar), Umkreis- und Duplikatprüfung; Moderierende prüfen und veröffentlichen | R10 |
| Vertraulichkeit | SSRF-Schutz bei Quellenprüfung und Seitenlesen | Nur `http`/`https`, nur öffentliche IP-Adressen (auch nach jeder Umleitung, höchstens drei), keine Cookies, 5 s Timeout; gelesen werden nur URLs aus den Suchergebnissen des Jobs, höchstens 1,5 MB HTML/Text bzw. 8 MB PDF (R10b) | R10 |
| Belastbarkeit | Kosten- und Lastgrenzen der KI-Suche | eine laufende Suche je Moderator, Tageslimit (`AI_SEARCH_DAILY_LIMIT`), begrenzte Tool-Aufrufe und Laufzeit, Wächter für hängende Jobs | R10 |
| Vertraulichkeit | Push ohne Personenbezug | Push-Titel und -Texte generisch je Art, Payload nur IDs und Badge-Zahl (E-04); Texte mit Namen und Festdaten entstehen erst beim Lesen der Liste in der API; Test `test_push_texts_are_generic` | R11 |
| Vertraulichkeit | Wohnort ohne GPS-Position | gespeichert werden nur PLZ, Ortsname und PLZ-Mittelpunkt (E-10); die App schickt keine Koordinaten an die Einstellungen | R11 |
| Belastbarkeit | Fan-out in Blöcken | Benachrichtigungen in Blöcken zu 500 Empfängern, je Block ein Push-Job; Idempotenz je Nutzer über `dedupe_key` (Erinnerung je Tag, Änderung je Stunde) | R11 |
