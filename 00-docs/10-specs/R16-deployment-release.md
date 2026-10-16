# R16 · Deployment und Release

| | |
|---|---|
| **Ziel** | Der Stadtfest-Finder läuft produktiv auf dem eigenen Server (EU) über Komodo. Die Apps sind über EAS gebaut und in den Stores eingereicht. Datenschutz-Doku und Betrieb sind vollständig. |
| **Hängt ab von** | alle vorherigen. **Empfehlung:** US1–US3 schon nach R05 umsetzen, dann per Inkrement erweitern. |
| **Quellen** | [CLAUDE.md „Git & CI/CD“, „External services“, „Privacy“](../../CLAUDE.md), Architektur |

## User Stories

### R16-US1 · Produktionsstack
- `infra/compose.yaml`:
  - Dienste `api`, `worker`, `mcp`, PostgreSQL + PostGIS, Redis, Nominatim (Deutschland)
  - Objektspeicher (EU-S3 oder selbst gehostetes SeaweedFS, per ADR)
  - Reverse Proxy mit TLS (Caddy oder Traefik, per ADR)
  - statische Auslieferung für die Deep-Link-Domain (R04)
- Images aus GHCR, getaggt mit Commit-SHA und SemVer. Komodo deployt eine festgelegte Version.
- Migrationen laufen als eigener Schritt vor dem Start der neuen API-Version (Alembic-Job). Nur rückwärtskompatible Migrationen bei laufendem Betrieb (Expand/Contract).
- Healthchecks und Restart-Policies für alle Dienste. Ressourcenlimits für Nominatim und Worker.

### R16-US2 · Konfiguration und Geheimnisse
- Alle Secrets liegen in Komodo bzw. GitHub Secrets, keine im Repo.
- Die Produktion startet nur mit vollständig validierten Settings (fail fast).
- Produktive Standards: `LLM_PROVIDER=mistral` oder `ollama`, `PUSH_PROVIDER` nach ADR.

### R16-US3 · Identität in Produktion
- Zitadel Cloud (EU-Region):
  - Projekt, App-Client, Rollen `user`, `moderator`, `category_admin`
  - Apple- und Google-IdP
  - Service-User für die Kontolöschung
  - E-Mail-Absender
- Anleitung: `40-operations/zitadel.md` (aus R05) für Produktion vervollständigen.

### R16-US4 · Backups und Wiederherstellung
- Tägliches PostgreSQL-Backup (verschlüsselt, EU-Ziel), Aufbewahrung 30 Tage. Das Objektspeicher-Backup ist gleich geregelt.
- Die Wiederherstellung wird einmal geprobt und im Runbook `40-operations/backup-restore.md` dokumentiert.
- Backups enthalten personenbezogene Daten. Das Löschkonzept beschreibt, wie Löschungen gegenüber Backups wirken (Ablauf nach 30 Tagen).

### R16-US5 · Beobachtbarkeit
- Strukturierte Logs zentral einsehbar (ohne personenbezogene Daten), Fehler-Alarm bei 5xx-Rate und fehlgeschlagenen Jobs (Outbox-Rückstau, KI-Jobs, Push-Fehler).
- Werkzeug per ADR, EU bzw. selbst gehostet.

### R16-US6 · Mobile-Release
- EAS-Build-Workflow (separat von den Docker-Images) für iOS und Android, Profile `preview` und `production`.
- App-Konfiguration: Bundle-IDs, Schemes, Associated Domains / App Links, Push-Credentials.
- **Store-Anforderungen:**
  - Datenschutzangaben (Privacy Nutrition Label, Data Safety)
  - Kontolöschung in der App (R05)
  - Sign in with Apple (R05)
  - Berechtigungstexte für Standort, Fotos und Mitteilungen auf Deutsch
- Impressum und Datenschutzerklärung als Links in der App (Drawer-Fußbereich bzw. Einstieg-Screen).

### R16-US7 · Datenschutz-Doku abschließen
- VVT, TOMs und Löschkonzept vollständig und mit dem Code abgeglichen: Jede Tabelle mit personenbezogenen Daten hat Zweck, Rechtsgrundlage, Frist und Löschweg.
- Liste aller Auftragsverarbeiter mit Standort und ADR-Verweis: Zitadel, Hosting, S3, LLM-Anbieter, Web-Suche, Expo/APNs/FCM, ggf. Kartenkacheln.
- Test-Suite „DeleteAccount vollständig“: Ein Nutzer mit Daten in allen Kontexten wird gelöscht, danach findet ein Schema-Scan keine Zeile mit seiner ID.

## Tests

- Smoke-Tests nach dem Deployment: Health, `GET /v1/categories`, `GET /v1/events`, MCP `search_events`.
- Vollständige Maestro-Suite gegen einen Staging-Build: Gastsuche, Login, Favoriten, Moderator veröffentlicht, KI-Suche mit Fake-Anbieter in Staging.

## Doku/Betrieb

Runbooks: `deployment-komodo.md`, `zitadel.md`, `backup-restore.md`, `eas-build.md`, `store-release.md`, `monitoring.md`, alle nach Vorlage.

## Definition of Done

- [ ] Ein Merge auf `main` führt über GHCR und Komodo zu einer laufenden Produktionsversion. Ein Rollback auf die vorherige Version ist dokumentiert und geprobt. *(Umgesetzt als HomeLab-Ablauf: Tag → Images → Renovate-PR im HomeLab → Deploy von Hand in Komodo, Rollback = vorheriger Tag; dokumentiert in `deployment-komodo.md`, lokal mit dem HomeLab-Stack geprobt. Offen: externe Einrichtung nach dem Runbook und die Rollback-Probe in Produktion.)*
- [ ] Die Apps sind als TestFlight- bzw. interne Testversion verfügbar. *(Im Repo fertig: `eas-build.yml`, `eas.json`, App-Konfiguration; offen: Store-Konten, `EXPO_TOKEN`, `ascAppId`, erster Build nach `eas-build.md` und `store-release.md`.)*
- [x] Datenschutz-Doku vollständig, der Löschtest ist grün. *(VVT Nr. 18–19, TOMs, Löschkonzept inkl. Backups, Auftragsverarbeiter; `test_delete_account_complete.py`. Vor dem Produktivstart: AV-Verträge, Entscheidung zu Cloudflare (ADR 0022) und rechtliche Prüfung der Rechtstexte.)*

## Umsetzungsnotizen

- Produktion läuft als HomeLab-Stack `stadtfest` (github.com/Harpune/HomeLab), nicht mit eigener Compose-Datei in diesem Repo. Dieses Repo liefert die Images `stadtfest-backend`, `-mcp`, `-edge`, `-searxng` und den Umgebungsvertrag `infra/komodo-environment.example` ([ADR 0019](../25-adr/0019-produktionsstack.md)).
- Entscheidungen: SeaweedFS, `stadtfest-edge` hinter dem HomeLab-Caddy, Hosts eine Ebene unter der Domain (Cloudflare-Zertifikat), `PUSH_PROVIDER=direct`; Loki/Alloy/Grafana im HomeLab-Stack `monitoring` ([ADR 0020](../25-adr/0020-beobachtbarkeit.md)); Backups über das HomeLab mit bis zu 6 Monaten Aufbewahrung ([ADR 0021](../25-adr/0021-backups.md)); Cloudflare als Eingang vorgeschlagen, Entscheidung offen ([ADR 0022](../25-adr/0022-eingang-cloudflare-tunnel.md)).
- Eine Kopie der laufenden SeaweedFS-Dateien ließ sich im Wiederherstellungstest nicht zurückspielen; der kalte Snapshot des HomeLab (Stack angehalten) ist konsistent.
- Der Schema-Scan fand Nutzer-IDs in Outbox-Payloads (Freunde, Listen, Einladungen); `delete_personal_data` löscht diese Nachrichten jetzt mit.
- Leere Variablen (`NAME=`) gelten als nicht gesetzt (`env_ignore_empty`); APNs/FCM-Schlüssel gehen auch als base64 (`APNS_KEY_BASE64`, `FCM_CREDENTIALS_BASE64`).
- Postgres-Healthcheck über TCP (`pg_isready -h 127.0.0.1`): Über den Socket meldet er sich beim ersten Start gesund, bevor die Datenbank existiert.
- Der Kontaktpunkt für Grafana-Alarme ist noch offen ([monitoring.md](../40-operations/monitoring.md)).
- Offen: die vollständige Maestro-Suite gegen einen Staging-Build. Sie braucht eine Staging-Umgebung, z. B. einen zweiten Stack mit `ENV=dev`, weil `ENV=prod` den Fake-KI-Anbieter ablehnt.
