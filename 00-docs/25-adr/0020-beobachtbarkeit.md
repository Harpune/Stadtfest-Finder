# 0020 · Beobachtbarkeit mit Grafana, Loki und Alloy im HomeLab

- **Status:** angenommen
- **Datum:** 2026-10-16 (am selben Tag überarbeitet: Werkzeuge im HomeLab-Stack `monitoring` statt im eigenen Stack)

## Kontext

R16-US5 verlangt zentral einsehbare, strukturierte Logs ohne personenbezogene Daten und Alarme bei hoher 5xx-Rate und fehlgeschlagenen Jobs (Outbox-Rückstau, KI-Jobs, Push-Fehler), selbst gehostet bzw. in der EU. Backend schreibt JSON-Zeilen mit `event` und `level`. Das HomeLab hatte nur Uptime Kuma und Dozzle.

## Entscheidung

1. **Loki, Alloy und Grafana im HomeLab-Stack `monitoring`**, für alle Stacks: Alloy liest die Container-Logs über den nur lesend eingebundenen Docker-Socket (wie Dozzle) und schickt sie mit den Labels `container`, `project` und `level` an Loki (Dateisystem, 30 Tage). Grafana unter `grafana.herderstreet.de`, nur im LAN und hinter Authentik.
2. **Alarmregeln des Stadtfest-Finders** im HomeLab (`stacks/monitoring/grafana/provisioning/alerting/stadtfest.yaml`):
   - 5xx-Rate von `stadtfest-api`/`stadtfest-mcp` über 5 % (mind. 5) in 5 Minuten,
   - fehlgeschlagene Jobs: `level` `error`/`critical` von `stadtfest-worker` sowie `ai_search_job_failed` und `outbox_relay_failed`,
   - Outbox-Rückstau: der Worker meldet alle 5 Minuten `outbox_backlog` (Anzahl, Alter der ältesten Nachricht); Alarm ab 300 s oder wenn die Meldung ausbleibt.
3. **Alarme auf Logs statt Metriken:** keine neue Python-Abhängigkeit, kein Metrik-Endpunkt.
4. Kontaktpunkt (E-Mail o. Ä.) wird in Grafana eingerichtet ([monitoring.md](../40-operations/monitoring.md)).

## Datenschutz

- Die Logs des Stadtfest-Finders enthalten keine Namen, E-Mails, Tokens, IP-Adressen, Koordinaten oder Freitexte (Log-Filter, Test `test_logging.py`; keine Access-Logs in `stadtfest-edge`, Uvicorn ohne Access-Log). Möglich sind interne IDs (z. B. `delete_idp_user:<subject>` bei `idp_deletion_failed`); deshalb 30 Tage Aufbewahrung ([VVT Nr. 19](../30-privacy/verarbeitungsverzeichnis.md)).
- Alles bleibt auf dem eigenen Server; Grafana sendet keine Nutzungsstatistiken.

## Konsequenzen

- Neue Log-Ereignisse, auf die alarmiert werden soll, brauchen `level=error` oder eine Ergänzung der Regel im HomeLab.
- Die laborweite Log-Historie enthält auch Logs anderer Dienste; dafür ist das HomeLab verantwortlich (dort dokumentiert).

## Verworfene Alternativen

- **Loki/Grafana im Stack `stadtfest`:** doppelte Werkzeuge im HomeLab.
- **Nur Uptime Kuma und Dozzle:** keine Alarme auf Log-Inhalte.
- **VictoriaLogs + vmalert, Sentry/GlitchTip, Prometheus-Metriken:** siehe Fassung vom 16.10.2026 im Git-Verlauf; mehr Dienste oder neue Abhängigkeiten ohne Vorteil hier.
