# Logs und Alarme (Grafana, Loki, Alloy)

## Zweck

Strukturierte Logs aller Dienste des Stacks zentral einsehen und bei Störungen alarmieren (R16-US5, [ADR 0020](../25-adr/0020-beobachtbarkeit.md)). Alloy liest die Container-Logs des Compose-Projekts `stadtfest`, Loki speichert sie 30 Tage, Grafana zeigt sie an und wertet die Alarmregeln aus `infra/observability/grafana/provisioning/alerting/rules.yaml` aus.

## Voraussetzungen

- Stack nach [deployment-komodo.md](deployment-komodo.md) deployt, Komodo-Secret `STADTFEST_GRAFANA_ADMIN_PASSWORD`
- SSH-Zugang zum Heimserver (Grafana ist nicht öffentlich)
- Für Benachrichtigungen per E-Mail: SMTP-Zugang (Host, Port, Nutzer, Passwort, Absender)

## Schritte

1. **Grafana öffnen:** `ssh -L 3000:127.0.0.1:3000 <server>` und dann `http://localhost:3000`, Anmeldung `admin` mit dem Passwort aus Komodo.
2. **Logs ansehen:** *Explore → Loki*, z. B.
   ```logql
   {stack="stadtfest", service="api"} | json | status >= 500
   {stack="stadtfest", service="worker"} | json | level="error"
   {stack="stadtfest"} | json | request_id="<id aus dem X-Request-ID-Header>"
   ```
3. **Kontaktpunkt einrichten** (noch offen, deshalb nicht provisioniert): *Alerting → Contact points → default* bearbeiten, z. B. E-Mail. Für E-Mail vorher SMTP in der Stack-Umgebung ergänzen und neu deployen:
   ```bash
   GF_SMTP_ENABLED=true
   GF_SMTP_HOST=smtp.example.eu:587
   GF_SMTP_USER=...
   GF_SMTP_PASSWORD=[[STADTFEST_GRAFANA_SMTP_PASSWORD]]   # Komodo-Secret
   GF_SMTP_FROM_ADDRESS=alerts@herderstreet.de
   ```
   und die Variablen im Dienst `grafana` in `infra/compose.yaml` unter `environment` durchreichen (PR). Alternativen: Telegram, ntfy, Webhook – alle in der Grafana-Oberfläche.
4. **Testalarm:** *Contact points → Test*.
5. Secrets nur in Komodo, **niemals ins Repo**.

### Alarmregeln

| Regel | Bedingung | Erste Schritte |
|---|---|---|
| <a id="5xx-rate"></a>**5xx-Rate API/MCP** | > 5 % Serverfehler (mind. 5) in 5 min, 5 min lang | `{service=~"api\|mcp"} \| json \| status >= 500` → `request_id` → Zeile mit `unhandled_exception` (Typ der Ausnahme); Readiness `GET /v1/health/ready` zeigt ausgefallene Abhängigkeiten |
| <a id="fehlgeschlagene-jobs"></a>**Fehlgeschlagene Jobs** | `level=error` von Worker/Backup, `ai_search_job_failed`, `outbox_relay_failed` in 15 min | Label `event` nennt den Fall: `push_failed` → [Push](push-apns-fcm.md); `idp_deletion_failed` → Nutzer von Hand löschen ([Zitadel](zitadel.md#nutzer-von-hand-löschen)); `ai_search_job_failed` → `error_code` (z. B. `search_unavailable`, [Web-Suche](web-suche.md)); `backup_failed` → [Backup](backup-restore.md) |
| <a id="outbox-rückstau"></a>**Outbox-Rückstau** | älteste offene Outbox-Nachricht > 300 s oder keine Meldung `outbox_backlog` (Worker aus) | Worker-Status in Komodo, Redis erreichbar? `{service="worker"} \| json \| event="outbox_relay_failed"` |
| **Backup fehlt** | 26 h kein `backup_succeeded` | [backup-restore.md](backup-restore.md), `docker compose logs backup` |

## Prüfung

- *Alerting → Alert rules*: Ordner „Stadtfest-Finder“ mit vier Regeln, Status *Normal* bzw. *Pending*, keine *Error*.
- *Explore*: `sum by (service) (count_over_time({stack="stadtfest"}[1h]))` zeigt alle Dienste.
- Lokal geprüft (16.10.2026): Regeln werden geladen und ausgewertet; eine eingespielte Zeile `push_failed` löst „Fehlgeschlagene Jobs“ aus, 8 von 20 Anfragen mit `500` setzen „5xx-Rate“ auf *Pending*, Zeilen `outbox_backlog` und `backup_succeeded` heben die beiden anderen Alarme auf.

## Rollback

- Einzelne Regel stummschalten: *Alerting → Silences* (zeitlich begrenzt).
- Monitoring ganz abschalten: Dienste `alloy`, `loki`, `grafana` stoppen; das Backend läuft unverändert weiter, Logs bleiben im Docker-Log (20 MB × 5 je Container).
- Logs vorzeitig löschen (z. B. nach einem Fehler im Log-Filter): Loki stoppen, Volume `loki-data` löschen, neu starten.
