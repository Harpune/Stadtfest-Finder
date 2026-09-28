# <Dienst/Aufgabe> einrichten

> Vorlage für Anleitungen zu externen Diensten und Betriebsaufgaben (CLAUDE.md „External services“). Datei kopieren, Platzhalter ersetzen, die Abschnitte beibehalten.

## Zweck

Wofür wird der Dienst gebraucht? Welches Inkrement bzw. ADR führt ihn ein?

## Voraussetzungen

- Zugänge und Rollen (z. B. Admin in Zitadel)
- Werkzeuge (CLI, Versionen)
- Vorher erledigte Anleitungen

## Schritte

1. …
2. …
3. Secrets hinterlegen: lokal in `.env` (siehe `.env.example`), in CI als GitHub Secret, in Produktion in Komodo. **Niemals ins Repo.**

## Prüfung

Wie erkennt man, dass alles funktioniert (Befehl, erwartete Ausgabe, Health-Endpunkt)?

## Rollback

Wie wird die Änderung rückgängig gemacht bzw. auf die vorherige Konfiguration zurückgeschaltet (z. B. per ENV auf `disabled` oder einen EU-Anbieter)?
