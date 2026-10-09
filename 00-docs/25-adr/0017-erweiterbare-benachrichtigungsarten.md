# 0017 · Benachrichtigungsarten sind erweiterbar

- **Status:** angenommen
- **Datum:** 2026-10-09

## Kontext

R11 hat `NotificationType` (`remind`, `near`, `change`, `cancel`) und den Zieltyp `NotificationTarget.type` (`event`) als Enums in der API festgelegt. R12 ergänzt `friend_added` und den Zieltyp `friend`; R13 und R14 bringen weitere Arten (`list_added`, `invite`, `rsvp_*`). Die CI-Prüfung `oasdiff` wertet neue Werte in einem Antwort-Enum als Breaking Change, weil ein Client, der alle Werte fest abfragt, an einem unbekannten Wert scheitern kann. Nach CLAUDE.md bräuchte jede neue Art eine neue API-Version.

## Entscheidung

- `NotificationType` und `NotificationTarget.type` sind **erweiterbare Enums**: Der Server darf jederzeit neue Werte liefern, ohne dass sich die API-Version ändert. Die Beschreibung im Vertrag (`api/openapi.yaml`) sagt das ausdrücklich.
- **Clients müssen unbekannte Werte vertragen:** Die App zeigt eine unbekannte Art mit neutralem Symbol (🔔) und der Art-Zeile „Benachrichtigung“, der Text kommt wie immer fertig vom Server (E-09). Ein Tipp auf ein unbekanntes Ziel markiert den Eintrag nur als gelesen.
- Die oasdiff-Meldungen „added the new … enum value“ für genau diese beiden Felder werden in `api/oasdiff-err-ignore.txt` mit Verweis auf dieses ADR eingetragen, je Inkrement die neuen Werte.
- Für alle anderen Enums gilt weiter: neue Werte in Antworten sind ein Breaking Change.

## Konsequenzen

- R13 und R14 brauchen für ihre neuen Arten keine neue API-Version, nur die Einträge in der Ignore-Liste.
- Ältere App-Versionen zeigen neue Arten mit dem neutralen Symbol, bis sie aktualisiert sind.

## Verworfene Alternativen

- **Neue API-Version je Art** (`/v2/me/notifications` …): viel Aufwand für eine App als einzigen Client; jede weitere Art bräuchte wieder eine Version.
- **Freitext statt Enum:** verliert die Typisierung im generierten Client und die Dokumentation der bekannten Werte.
