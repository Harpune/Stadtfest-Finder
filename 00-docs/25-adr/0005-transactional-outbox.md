# 0005 · Domain-Events über Transactional Outbox

- **Status:** angenommen (Umsetzung in R07)
- **Datum:** 2026-09-28
- **Bezug:** E-13

## Kontext

Aktionen wie „Fest veröffentlichen“ ändern Daten und lösen Folgearbeit aus (Cache-Invalidierung, Benachrichtigungen). Wird ein Job direkt nach dem Commit eingereiht, geht er bei einem Absturz dazwischen verloren. Wird er vor dem Commit eingereiht, bezieht er sich eventuell auf Daten, die nie gespeichert wurden.

## Entscheidung

- Domain-Events werden **in derselben Transaktion** wie die fachliche Änderung in die Tabelle `outbox` geschrieben: `id`, `type`, `payload` (nur IDs), `occurred_at`, `dispatched_at`.
- Ein Relay im Worker liest unversandte Einträge (Polling bzw. `LISTEN/NOTIFY`) und reiht sie in arq ein.
- Konsumenten sind idempotent über die Event-ID.

## Konsequenzen

- Zustellung „at least once“, keine verlorenen Events.
- Versendete Einträge werden nach 14 Tagen gelöscht.
- Payloads enthalten keine personenbezogenen Inhalte, nur IDs.

## Verworfene Alternativen

- Direktes Enqueue in arq: Risiko verlorener bzw. verwaister Events.
- Externer Message-Broker (RabbitMQ, Kafka): zusätzliche Infrastruktur ohne Mehrwert bei dieser Last.
