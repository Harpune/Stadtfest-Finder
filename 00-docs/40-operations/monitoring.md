# Logs und Alarme (Grafana, Loki, Alloy im HomeLab)

## Zweck

Strukturierte Logs zentral einsehen und bei Störungen alarmieren (R16-US5, [ADR 0020](../25-adr/0020-beobachtbarkeit.md)). Loki, Alloy und Grafana laufen im HomeLab-Stack `monitoring` für alle Stacks; der Stadtfest-Finder liefert nur JSON-Logs und seine Alarmregeln (HomeLab `stacks/monitoring/grafana/provisioning/alerting/stadtfest.yaml`). Logs bleiben 30 Tage.

## Voraussetzungen

- HomeLab-Stack `monitoring` mit Loki, Alloy und Grafana deployt (`make monitoring-up` per SSH, HomeLab README „monitoring“)
- In Authentik eine Anwendung für Grafana, dem eingebetteten Outpost zugewiesen (wie bei Dozzle)
- Für Alarm-E-Mails: SMTP-Zugang eines Mailanbieters

### Werte, die hier gebraucht werden

| Wert | Quelle | wird eingetragen in |
|---|---|---|
| Grafana-Admin-Passwort (nur Notfall) | `openssl rand -hex 32` | `GF_SECURITY_ADMIN_PASSWORD` in `stacks/monitoring/.env` auf dem Server (diese Datei ist im HomeLab handgeschrieben, nicht Komodo) |
| SMTP-Host, Nutzer, Passwort, Absender | Mailanbieter | `GF_SMTP_ENABLED=true`, `GF_SMTP_HOST`, `GF_SMTP_USER`, `GF_SMTP_PASSWORD`, `GF_SMTP_FROM_ADDRESS` in `stacks/monitoring/.env` |
| Empfänger der Alarme | selbst | Grafana → *Alerting → Contact points* |

## Schritte

1. **Authentik:** *Applications → Create with provider* → Proxy-Provider *Forward auth (single application)*, External host `https://grafana.herderstreet.de` → die Anwendung dem *authentik Embedded Outpost* zuweisen (wie bei Dozzle, HomeLab `docs/SERVICES.md` §1).
2. **Grafana öffnen:** `https://grafana.herderstreet.de` (nur im LAN bzw. über Tailscale; Anmeldung über Authentik, Grafana übernimmt den Nutzer aus den `X-Authentik-*`-Headern).
3. **E-Mail (optional):** die `GF_SMTP_*`-Werte in `stacks/monitoring/.env` setzen und `make monitoring-up` ausführen.
4. **Kontaktpunkt:** *Alerting → Contact points → default* bearbeiten (E-Mail-Adresse, oder Telegram/ntfy/Webhook) → *Test*. Alle Regeln laufen über die Standard-Benachrichtigungsrichtlinie.
5. **Logs ansehen:** *Explore → Loki*, z. B.
   ```logql
   {container="stadtfest-api"} | json | status >= 500
   {container="stadtfest-worker"} | json | level="error"
   {project="stadtfest"} | json | request_id="<id aus dem X-Request-ID-Header>"
   ```

### Alarmregeln (Ordner „Stadtfest-Finder“)

| Regel | Bedingung | Erste Schritte |
|---|---|---|
| <a id="5xx-rate"></a>**5xx-Rate API/MCP** | > 5 % Serverfehler (mind. 5) in 5 min, 5 min lang | `{container=~"stadtfest-api\|stadtfest-mcp"} \| json \| status >= 500` → `request_id` → Zeile mit `unhandled_exception` (Typ der Ausnahme); `GET /v1/health/ready` zeigt ausgefallene Abhängigkeiten |
| <a id="fehlgeschlagene-jobs"></a>**Fehlgeschlagene Jobs** | `level=error` vom Worker, `ai_search_job_failed`, `outbox_relay_failed` in 15 min | Label `event` nennt den Fall: `push_failed` → [Push](push-apns-fcm.md); `idp_deletion_failed` → Nutzer von Hand löschen ([Zitadel](zitadel.md#nutzer-von-hand-löschen)); `ai_search_job_failed` → `error_code` (z. B. `search_unavailable`, [Web-Suche](web-suche.md)) |
| <a id="outbox-rückstau"></a>**Outbox-Rückstau** | älteste offene Outbox-Nachricht > 300 s oder keine Meldung `outbox_backlog` (Worker aus) | Worker-Status in Komodo, Redis erreichbar? `{container="stadtfest-worker"} \| json \| event="outbox_relay_failed"` |

Backups überwacht das HomeLab selbst (`make backup` ist ein Skript, kein Container).

## Prüfung

- *Alerting → Alert rules*: Ordner „Stadtfest-Finder“ mit drei Regeln, Status *Normal* bzw. *Pending*, keine *Error*. Solange der Stack `stadtfest` nicht läuft, steht „Outbox-Rückstau“ auf *Alerting* (keine Meldung vom Worker) – gewollt.
- *Explore*: `sum by (container) (count_over_time({project="stadtfest"}[1h]))` zeigt die Container des Stacks.

**Lokal geprüft (16.10.2026):** HomeLab-Monitoring (Loki, Alloy, Grafana) zusammen mit dem HomeLab-Stack `stadtfest`: Regeln werden geladen und ausgewertet, Loki erhält die Logs aller `stadtfest-*`-Container mit den Labels `container` und `project`. Mit eingespielten Zeilen ausgelöst wurden die Regeln vorher im R16-Stand (gleiche Abfragen, andere Labels).

## Rollback

- Einzelne Regel stummschalten: *Alerting → Silences* (zeitlich begrenzt).
- Monitoring abschalten: Container `loki`, `alloy`, `grafana` im HomeLab stoppen; der Stadtfest-Finder läuft unverändert weiter, Logs bleiben im Docker-Log und in Dozzle.
