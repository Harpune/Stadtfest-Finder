# 0020 · Beobachtbarkeit mit Grafana, Loki und Alloy (selbst gehostet)

- **Status:** angenommen
- **Datum:** 2026-10-16

## Kontext

R16-US5 verlangt zentral einsehbare, strukturierte Logs ohne personenbezogene Daten und Alarme bei hoher 5xx-Rate und fehlgeschlagenen Jobs (Outbox-Rückstau, KI-Jobs, Push-Fehler). Das Werkzeug soll in der EU bzw. selbst gehostet laufen. Backend und Backup schreiben bereits JSON-Zeilen mit `event` und `level`; Metriken (Prometheus) gibt es bisher nicht.

## Entscheidung

1. **Grafana Alloy** sammelt die Logs der Container dieses Compose-Projekts (Docker-Socket nur lesend, andere Stacks auf dem Host werden ignoriert) und schickt sie an **Loki** (Einzelprozess, Dateisystem, Aufbewahrung 30 Tage). Einziges ausgewertetes Label ist `level`, alle anderen Felder liest LogQL mit `| json` erst bei der Abfrage.
2. **Grafana** stellt Loki als Datenquelle bereit und wertet vier Alarmregeln aus (`infra/observability/grafana/provisioning/alerting/rules.yaml`):
   - 5xx-Rate von API und MCP-Server über 5 % (mindestens 5 Fehler) in 5 Minuten,
   - fehlgeschlagene Jobs: Zeilen mit `level` `error`/`critical` von Worker und Backup sowie `ai_search_job_failed` und `outbox_relay_failed`,
   - Outbox-Rückstau: der Worker meldet alle 5 Minuten `outbox_backlog` mit Anzahl und Alter der ältesten offenen Nachricht; Alarm ab 300 s oder wenn die Meldung ausbleibt,
   - fehlendes Backup: kein `backup_succeeded` in 26 Stunden.
3. **Alarme als Logs statt Metriken:** Es kommt keine Python-Abhängigkeit (z. B. `prometheus-client`) und kein Metrik-Endpunkt hinzu. Die Messwerte stehen in denselben Zeilen, die auch für die Fehlersuche gebraucht werden.
4. Grafana ist **nicht öffentlich** erreichbar (nur `127.0.0.1`, Zugriff per SSH-Tunnel). Der Kontaktpunkt für Benachrichtigungen (z. B. E-Mail) wird bei der Einrichtung festgelegt ([monitoring.md](../40-operations/monitoring.md)).

## Datenschutz

- Die Logs enthalten keine Namen, E-Mails, Tokens, IP-Adressen, Koordinaten oder Freitexte (Log-Filter, Test `test_logging.py`; Caddy und Uvicorn schreiben keine Access-Logs). Möglich sind interne IDs (z. B. Job-IDs mit IdP-Subject bei `idp_deletion_failed`); deshalb gilt eine feste Aufbewahrung von 30 Tagen ([VVT Nr. 19](../30-privacy/verarbeitungsverzeichnis.md)).
- Alle Daten bleiben auf dem eigenen Server; Grafana sendet keine Nutzungsstatistiken (Reporting und Update-Prüfung aus).

## Konsequenzen

- Drei zusätzliche Container (zusammen etwa 1,5 GB RAM).
- Neue Log-Ereignisse, auf die alarmiert werden soll, brauchen `level=error` oder eine Ergänzung der Regel.

## Verworfene Alternativen

- **VictoriaLogs + vmalert:** leichter, aber weniger verbreitet und ein zusätzlicher Alertmanager.
- **Dozzle + Uptime Kuma:** einfach, aber ohne Alarme auf Log-Inhalte (5xx-Rate, Job-Fehler).
- **Sentry/GlitchTip:** gut für Ausnahmen, aber keine zentrale Log-Ansicht; Sentry Cloud wäre ein Verarbeiter außerhalb der EU.
- **Prometheus-Metriken im Backend:** genauer für Raten, aber neue Abhängigkeit und ein weiterer Dienst.
