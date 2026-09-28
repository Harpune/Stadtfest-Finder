# Löschkonzept

> Stand R01: noch keine personenbezogenen Daten gespeichert. Ab R05 beschreibt dieses Dokument den Use Case `DeleteAccount`. Jedes Inkrement mit Personenbezug erweitert Tabelle und Tests im selben PR.

## Aufbewahrung und Löschung je Datenart

| Datenart (Tabelle) | Personenbezug | Aufbewahrung | Löschweg | Test | Inkrement |
|---|---|---|---|---|---|
| – | – | – | – | – | – |

## Kontolöschung (ab R05)

1. `DELETE /v1/me` löscht alle personenbezogenen Daten des Nutzers im Backend in einer Transaktion.
2. Der Nutzer wird über den IdP-Admin-Port beim IdP gelöscht; bei Fehler Retry-Job.
3. Audit-Felder mit der Nutzer-ID werden auf `null` gesetzt.

## Backups

Wirkung von Löschungen auf Backups: folgt in R16 (Ablauf der Backup-Aufbewahrung).
