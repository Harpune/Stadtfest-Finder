# R04 · Fest-Details

| | |
|---|---|
| **Ziel** | Alle Infos zu einem Fest ansehen und von dort handeln: Route starten, Website öffnen, teilen. Account-Aktionen (Herz, Einladen) führen Gäste freundlich zum Gast-Hinweis. |
| **Hängt ab von** | R03 |
| **Quellen** | [02 Fest-Details](../15-design/workflows/02-fest-details.md), [03 Gast-Hinweis](../15-design/workflows/03-authentifizierung.md), [Design-Referenz §4–5](../15-design/design/design-referenz.md#4-detailseite-detail), Screens 02-01 bis 02-05, 03-01 bis 03-03 |
| **Rollen** | Gast |

## Umfang

**Drin:** Detailseite, Galerie mit Platzhalter, Infoblock, Beschreibung, Programm, Ort mit Mini-Karte, Anfahrt, Website, fixe Fußleiste, Zustände (laden, abgesagt, 404), Deep Link `https://stadtfest-finder.de/f/{id}`, Gast-Hinweis-Sheet mit `pendingAction`, Seitenstapel-Navigation.

**Nicht drin:**
- Login hinter „Anmelden oder registrieren“ (R05; bis dahin öffnet der Button einen Platzhalter)
- Favorit und Einladen für Nutzer (R06 bzw. R14)
- Echte Bilder (R08)

## User Stories

### R04-US1 · Detailseite öffnen
- Die Detailseite öffnet sich aus Karussell (zweiter Tipp), Liste, später Zeitleiste, Listen und Benachrichtigungen. Sie schiebt sich in 340 ms von rechts herein.
- Titel und Eckdaten aus der Listenantwort erscheinen **sofort** (TanStack-Query-Platzhalterdaten). Die übrigen Abschnitte zeigen Skeletons, bis `GET /v1/events/{id}` da ist.
- Unterseiten liegen als Stapel. „Zurück“ schließt nur die oberste.

### R04-US2 · Inhalte darstellen
- **Galerie** 340 hoch:
  - Tipp links/rechts blättert, Punkte zeigen die Position (aktiv 18 × 5 Amber), dazu der Zähler „1 / n“.
  - Ohne Bilder erscheint der gestreifte Platzhalter.
  - Schwebende Buttons: Zurück, Teilen, Herz (44, glass).
- **Kopf:** Pills für Kategorie und Status, Titel (Serif 36), „{Ort}, {Stadt} · {km} km entfernt“ (Entfernung nur mit Standort).
- **Infoblock:** Zeitraum, Öffnungszeiten (mehrzeilig), Eintritt, jeweils mit Icon-Kachel.
- **Abschnitte:**
  - „Über das Fest“
  - „Programm & Highlights“: Wochentag + Datum in Rosa, Titel und Untertitel. Der Abschnitt entfällt ohne Programm.
  - „Ort“: Mini-Karte 160 hoch mit Amber-Pin und Adresse
  - „Anfahrt“: ÖPNV und Parken getrennt, entfällt ohne Angaben
  - „Offizielle Website ↗“, entfällt ohne URL
- **Fußleiste:** „Route starten“ (Amber) und „Einladen“ (surface2).

### R04-US3 · Route und Website
- „Route starten“ oder ein Tipp auf die Mini-Karte öffnet die Standard-Karten-App mit Zielkoordinaten und Namen: iOS Apple Maps, Android `geo:`-Intent bzw. Google Maps.
- „Offizielle Website“ öffnet den In-App-Browser (`expo-web-browser`). Nur `https`/`http`-URLs sind zulässig, alles andere wird nicht geöffnet.

### R04-US3a · Teilen (auch als Gast)
- „Teilen“ öffnet für **alle**, auch Gäste, das native Share-Sheet mit Name, Zeitraum und Link `https://{EXPO_PUBLIC_LINK_HOST}/f/{id}` (Standard `stadtfest.herderstreet.de`).
- Der Link enthält nur die Fest-ID; ans Backend geht nichts.
- Entscheidung vom 29.09.2026: Teilen braucht kein Konto. Der Gast-Hinweis „Feste teilen“ (Screen 03-02) entfällt.

### R04-US4 · Abgesagt und nicht verfügbar
- **Abgesagt:** rote Pill „Abgesagt“ auf `roseSoft`. Ein Absagegrund steht als Hinweis unter dem Titel (Annahme). „Einladen“ ist deaktiviert, die übrigen Aktionen bleiben erreichbar.
- **404:** Hinweis „Dieses Fest ist nicht mehr verfügbar“, danach zurück zur Karte.

### R04-US5 · Gast-Hinweis mit gemerkter Aktion
Als Gast will ich bei Herz oder Einladen erfahren, was ein Konto bringt, ohne blockiert zu werden.

- Bottom Sheet mit Icon-Kachel (Herz oder Personen), Titel und Text wörtlich aus der Design-Referenz §5. Buttons: „Anmelden oder registrieren“ und „Weiter ohne Konto“.
- Die Aktion wird als `pendingAction {type: favorite|invite, eventId}` im Auth-Store gemerkt.
- „Weiter ohne Konto“ oder ein Tipp auf den Hintergrund schließt das Sheet und verwirft `pendingAction`.
- Gilt überall, wo diese Aktionen vorkommen: Detailseite und Herz in der Liste (R03).

### R04-US6 · Deep Link auf ein Fest
- `https://stadtfest-finder.de/f/{eventId}` und `stadtfest://f/{eventId}` öffnen die Detailseite, auch beim Kaltstart. Darunter liegt die Karte als Stapelbasis.
- Die Universal Links (iOS) und App Links (Android) sind konfiguriert.
- Die Domain liefert `apple-app-site-association` und `assetlinks.json` aus, ohne installierte App eine einfache Weiterleitungsseite zu den Stores (statische Datei, keine Web-App).

## Mobile-Struktur

- Screen `src/app/f/[id].tsx`, Logik in `src/features/event-detail/`.
- Komponenten mit Story:
  - Galerie und Kopf: `Gallery`, `StatusPill`, `CategoryPill`
  - Inhalte: `InfoBlock`, `SectionHeader`, `ProgramList`, `MiniMap`, `LinkRow`
  - Rahmen und Sheets: `StickyFooter`, `GuestHintSheet`
- `testID`s: `detail.back`, `detail.share`, `detail.favorite`, `detail.route`, `detail.invite`, `detail.website`, `guestHint.login`, `guestHint.dismiss`.

## Tests

- RNTL: Abschnitte entfallen ohne Daten, Zustand abgesagt (Einladen deaktiviert), 404-Hinweis, Gast-Hinweis setzt und verwirft `pendingAction`.
- Jest: URL-Validierung für die Website, Aufbau der Karten-URLs je Plattform.
- Maestro: Gastsuche → Detail → Herz → Gast-Hinweis → „Weiter ohne Konto“. Außerdem Deep-Link-Öffnung per `openLink`.

## Doku/Betrieb

- `40-operations/deep-links-domain.md`: DNS, Auslieferung von AASA/assetlinks (Team-ID, SHA-256-Fingerprint aus EAS), Prüfung mit den Validatoren von Apple und Google.

## Definition of Done

- [ ] Screens 02-01 bis 02-05 und 03-01 bis 03-03 in dunkel und hell umgesetzt.
- [ ] Deep Link funktioniert beim Kalt- und Warmstart auf iOS und Android (Simulator/Emulator).
- [ ] Stories für alle neuen Komponenten.
