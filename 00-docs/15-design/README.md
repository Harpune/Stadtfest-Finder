# Stadtfest-Finder: Spezifikation

Mobile App (iOS und Android, plattformneutral) zum Entdecken von Stadtfesten, Volksfesten & Kirmes, Weihnachtsmärkten und Märkten in Deutschland. App-Sprache: Deutsch.

Dieser Ordner lässt sich als `00-docs/15-design/` in ein Repository übernehmen. Alle Inhalte sind Markdown, Bilder werden relativ eingebunden und auf GitHub/GitLab direkt angezeigt, Mermaid-Diagramme inklusive.

## Aufbau

```text
15-design/
├── README.md                     ← diese Datei (Einstieg, Konventionen)
├── 00-ueberblick/
│   ├── gesamtworkflow.md         ← App-Navigation und alle Teil-Workflows im Zusammenhang
│   ├── rollen-und-rechte.md      ← Gast, Nutzer, Moderator: wer darf was
│   └── screen-inventar.md        ← alle Screens mit Screenshot, Workflow und Prototyp-Zustand
├── workflows/                    ← Teil-Workflows (Schritte, Backend, sync/async, Moderation)
│   ├── 01-stadtfest-suche.md
│   ├── 02-fest-details.md
│   ├── 03-authentifizierung.md
│   ├── 04-favoriten-und-zeitleiste.md
│   ├── 05-gemeinsame-listen.md
│   ├── 06-einladungen.md
│   ├── 07-benachrichtigungen.md
│   ├── 08-moderation-feste.md
│   ├── 09-moderation-ki-suche.md
│   └── 10-moderation-kategorien.md
├── backend/
│   ├── api-endpunkte.md          ← alle Endpunkte mit Rolle und Ausführungsmodus
│   ├── datenmodell.md            ← Entitäten und Felder
│   └── ereignisse-und-jobs.md    ← Domain-Events, Hintergrundjobs, Push-Regeln
├── design/
│   ├── theme-farben.md           ← semantische Farben (primary, secondary, error, warning …) dunkel/hell
│   ├── theme-farben.png
│   ├── design-tokens.json        ← dieselben Farben maschinenlesbar
│   └── design-referenz.md        ← Typografie, Radien, Abstände, Bewegung, Screen-Maße
├── screenshots/                  ← 58 Screens, 780 × 1688 px (2×), Dateiname = Screen-ID
└── prototyp/
    └── StadtfestFinder-Prototyp.html  ← klickbarer Prototyp, offline per Doppelklick
```

## Lesereihenfolge

1. [Gesamtworkflow](00-ueberblick/gesamtworkflow.md): Überblick über alle Wege durch die App.
2. [Rollen und Rechte](00-ueberblick/rollen-und-rechte.md).
3. Die Teil-Workflows in `workflows/`, jeweils eigenständig lesbar.
4. [API](backend/api-endpunkte.md), [Datenmodell](backend/datenmodell.md) und [Ereignisse](backend/ereignisse-und-jobs.md) als Referenz für die Umsetzung.

## Teil-Workflows

| Nr. | Workflow | Rollen | Moderationsansicht |
|---|---|---|---|
| 01 | [Stadtfest-Suche (Karte, Liste, Suche, Filter)](workflows/01-stadtfest-suche.md) | Gast, Nutzer | nein; zeigt nur veröffentlichte Feste und aktive Kategorien |
| 02 | [Fest-Details](workflows/02-fest-details.md) | Gast, Nutzer | nein; Inhalte kommen aus 08 |
| 03 | [Authentifizierung](workflows/03-authentifizierung.md) | Gast → Nutzer | nein |
| 04 | [Favoriten und Zeitleiste (Profil-Drawer)](workflows/04-favoriten-und-zeitleiste.md) | Nutzer | Einstieg in die Moderationsansicht (nur Moderatoren) |
| 05 | [Gemeinsame Listen](workflows/05-gemeinsame-listen.md) | Nutzer | nein |
| 06 | [Einladungen](workflows/06-einladungen.md) | Nutzer | nein |
| 07 | [Benachrichtigungen und Einstellungen](workflows/07-benachrichtigungen.md) | Nutzer | nein; Auslöser kommen teils aus 08 |
| 08 | [Moderation: Feste](workflows/08-moderation-feste.md) | Moderator | **ja** |
| 09 | [Moderation: KI-Suche per PLZ](workflows/09-moderation-ki-suche.md) | Moderator | **ja** |
| 10 | [Moderation: Kategorien](workflows/10-moderation-kategorien.md) | Moderator | **ja** |

## Konventionen in den Workflow-Dokumenten

Jede Workflow-Datei hat denselben Aufbau: Steckbrief, Screens, Ablaufdiagramm, Schritt-Tabelle, Zustände, Regeln, offene Punkte.

In der Spalte **Modus** der Schritt-Tabellen:

| Modus | Bedeutung |
|---|---|
| **lokal** | Kein Backend-Aufruf. Zustand nur im Client (z. B. Filter-Entwurf, Navigation). |
| **sync** | Request/Response. Der Client wartet auf die Antwort (Spinner oder optimistisches Update mit Rollback bei Fehler). |
| **async** | Der Client bekommt nur eine Bestätigung (`202 Accepted` oder `200` mit Job-ID). Die eigentliche Verarbeitung läuft im Hintergrund, das Ergebnis kommt per Push, Polling oder beim nächsten Laden. |
| **sync + async** | Sync-Antwort für den Aufrufer, zusätzlich löst der Server Hintergrundarbeit aus (z. B. Push an andere Nutzer). |

Endpunkte sind als `METHODE /pfad` angegeben, Details in [api-endpunkte.md](backend/api-endpunkte.md). Screen-IDs (z. B. `02-01`) entsprechen den Dateinamen in `screenshots/`.

## Prototyp

`prototyp/StadtfestFinder-Prototyp.html` ist der klickbare Prototyp. Er enthält Beispieldaten, simuliert alle Backend-Aufrufe und zeigt Verhalten, Übergänge und Texte. Er ist **Design-Referenz, kein Produktionscode**.

## Annahmen

- Stichtag der Beispieldaten ist **Freitag, 25.09.2026**. Standort und Beispiel-Wohnort ist Aalen. Die Moderator-Region „Ostalb“ der Screens gibt es seit ADR 0015 nicht mehr.
- Namen, Freunde, Nachrichten und KI-Funde sind fiktive Beispieldaten.
- Die Backend-Schnittstellen sind aus dem Verhalten des Prototyps abgeleitet und als Vorschlag zu verstehen.
