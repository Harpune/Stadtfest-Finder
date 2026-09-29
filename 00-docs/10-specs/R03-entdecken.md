# R03 · Entdecken: Karte, Liste, Suche, Filter

| | |
|---|---|
| **Ziel** | Gäste öffnen die App und finden Feste in ihrer Nähe auf Karte und Liste, grenzen sie per Suche, Kategorie-Chip und Filter-Sheet ein und wechseln verlustfrei zwischen beiden Ansichten. |
| **Hängt ab von** | R02 |
| **Quellen** | [01 Stadtfest-Suche](../15-design/workflows/01-stadtfest-suche.md), [Design-Referenz §1–3](../15-design/design/design-referenz.md#1-kartenansicht--startseite-karte), Screens 01-01 bis 01-09 |
| **Rollen** | Gast (Nutzer und Moderator gleich) |
| **Flow** | A |

## Umfang

**Drin:** Startscreen mit Karte (MapLibre), Marker/Cluster/Auswahl-Pille, Karussell, Liste, Suchfeld, Kategorie-Chips, Filter-Sheet (Zeitraum mit Monatsraster, Kategorie, Entfernung), Lade-, Leer- und Fehlerzustände, Standortfreigabe, Offline-Lesen, Profilbild-Button (Gast-Icon, öffnet einen Platzhalter bis R05).

**Nicht drin:** Detailseite (R04). Das Herz in der Liste ist sichtbar, der Tipp darauf öffnet ab R04 den Gast-Hinweis. Den Favoriten-Zustand gibt es ab R06.

## User Stories

### R03-US1 · App-Start mit Standort
- Beim ersten Start fragt die App **einmal** nach der Standortfreigabe (Systemdialog, vorher kein eigener Screen).
- **Freigabe erteilt:** Die Karte zentriert auf die Position, Zoom 10. Der eigene Standort erscheint als blauer Punkt (`meDot`).
- **Freigabe abgelehnt:** Start auf dem zuletzt bekannten Kartenausschnitt (lokal gespeichert), sonst Deutschland-Mitte (≈ 51.16 N, 10.45 E, Zoom 6). Die Entfernung wird dann zum Kartenmittelpunkt berechnet.
- Während des Ladens: Skeleton-Karten im Karussell und Pille „Feste werden geladen …“ (01-02).
- Die Standortposition verlässt das Gerät **nicht**: Entfernungen berechnet die App selbst (Haversine). Sie wird nie gespeichert, weder lokal noch im Backend.
- **Kartenausschnitt statt Umkreis** (Entscheidung 29.09.2026): Einzige räumliche Einschränkung ist der sichtbare Kartenausschnitt. Es gibt keinen Umkreis-Filter; eingegrenzt wird durch Zoomen.

### R03-US2 · Karte bedienen
- Zoom 6–13.
- Beim Verschieben oder Zoomen lädt die App nach 300 ms Pause für den neuen Ausschnitt nach. Bereits geladene Marker bleiben stehen, bis die Antwort da ist.
- Geladen wird ein um 30 % je Seite erweiterter, auf ein Raster ausgerichteter Bereich (`features/discover/geo.ts`). Kleine Verschiebungen treffen so dieselbe (gecachte) Antwort. Karussell, Liste und Leerzustand zeigen nur Feste im sichtbaren Ausschnitt; Zählungen (`/count`) gelten für den sichtbaren Ausschnitt.
- **Marker:** 38-pt-Kreis in `surface2`, 2 px Rand in der Kategorie-Farbe, Emoji 17 pt.
- **Cluster** (MapLibre, Radius 46 px): 44-pt-Kreis in Rosa mit Zahl. Ein Tipp zoomt 2 Stufen auf den Schwerpunkt.
- **Auswahl:**
  - Tippen auf einen Pin macht ihn zur Amber-Pille mit Kurznamen (links oder rechts ausgerichtet je nach Bildschirmhälfte).
  - Der ausgewählte Marker ist **nie Teil eines Clusters**. Er liegt in einer eigenen Ebene und wird aus der Cluster-Quelle herausgefiltert.
  - Das Karussell scrollt zur passenden Karte.
- Ein zweiter Tipp auf Pin oder Karussellkarte öffnet die Detailseite (ab R04, bis dahin ein Toast-Platzhalter).
- Kartensteuerung: +/−, Standort-Button (zentriert auf die Position, Zoom 10, lädt nach).
- Kartenstil: OSM-basierte Vektorkacheln mit dunklem und hellem Stil passend zum Theme (Quelle per ADR, siehe offene Punkte). Die Attribution „© OpenStreetMap-Mitwirkende“ ist sichtbar.

### R03-US3 · Karussell
- Horizontal mit Scroll-Snap, Karten 300 × ≈ 106, **zeitlich sortiert** (API-Sortierung).
- Das Wischen wählt den mittigen Eintrag als Pin aus. Liegt der Pin außerhalb des Ausschnitts, verschiebt sich die Karte so weit, dass er sichtbar wird.
- Karteninhalt:
  - Bild 84 × 84 (Platzhalter bis R08)
  - Status-Text: „● Läuft · noch X Tage“ (Amber), „In X Tagen“ bei ≤ 14 Tagen (Rosa), sonst „Ab {Datum}“; abgesagt: „Abgesagt“ (Rosa)
  - Name, Zeitraum, „{Emoji} {Ort} · {km} km“
- Die ausgewählte Karte hat einen Amber-Rahmen.
- Die Status-Texte berechnet **eine gemeinsame Funktion** (`features/events/status.ts`) mit Tests. Liste, Detail und Zeitleiste nutzen sie wieder.

### R03-US4 · Liste
- Umschalter Karte/Liste unten mittig (Segmented Control). Der Wechsel lädt nicht neu. Suche, Filter und Auswahl bleiben erhalten.
- Kopf: „{n} Feste im Kartenausschnitt“, rechts „nach Datum“. Darunter „um {Ort}“ (Ortsname der Kartenmitte über `/v1/geocode/reverse`) und „Ausschnitt ändern“ (wechselt zur Karte).
- Sortierung immer nach Datum; eingegrenzt wird nur durch den Ausschnitt.
- Karten: Bild 160 hoch, Badge „● Läuft gerade“, Herz-Button (glass), Status, Name (Serif 20), „{Zeitraum} · {Ort}“, Pills für Kategorie und Entfernung.
- Endloses Scrollen per `cursor`. Pull-to-Refresh lädt neu.

### R03-US5 · Suche
- Suchfeld „Fest oder Ort suchen“ im schwebenden Header. Ab 2 Zeichen wird nach 300 ms gesucht (`q`). ✕ leert die Suche.
- Die Suche gilt für Karte und Liste gemeinsam.
- Ohne Treffer: „Kein Fest für ‚{q}‘“ mit Hinweis auf die Schreibweise (01-08).
- Die Suche gilt im sichtbaren Ausschnitt. Ist der Text ein Ort oder eine PLZ (`/v1/geocode`, erster Treffer vom Typ Stadt/PLZ), erscheint unter dem Suchfeld „Zu {Ort} springen“. Ein Tipp fliegt die Karte dorthin (Zoom 11), leert die Textsuche und schließt die Tastatur.

### R03-US6 · Kategorie-Chips
- Horizontal scrollbare Chip-Reihe. Zuerst der Zeitraum-Chip mit ▾ (öffnet das Filter-Sheet), danach „{Emoji} {Name} {Anzahl}“ in Moderationsreihenfolge.
- Mehrfachauswahl. Ein aktiver Chip ist Amber mit Text `#15111C`.
- Die Anzahl kommt aus `byCategory` von `/v1/events/count`.
- Ein Ziehen der Reihe löst keinen Chip aus.
- Ist eine gewählte Kategorie nach dem Neuladen der Kategorien nicht mehr vorhanden, entfällt sie stillschweigend aus dem Filter.

### R03-US7 · Filter-Sheet
- Bottom Sheet (01-05). Es bearbeitet eine **Kopie** der aktuellen Filter (Entwurf):
  - **Zeitraum:** „Alle Termine“, „Heute“, „Dieses Wochenende“, „Zeitraum wählen“. Die letzte Option zeigt ein Monatsraster für die nächsten 12 Monate mit Mehrfachauswahl (01-06, E-03).
  - **Kategorie:** Chips mit Mehrfachauswahl, nur aktive.
  - ~~Entfernung~~: entfällt (Kartenausschnitt statt Umkreis).
- Der Primär-Button „{n} Feste anzeigen“ zählt live mit (`/count`, debounced 300 ms). Bei 0 heißt er „Keine Treffer – trotzdem anwenden“.
- „Zurücksetzen“ setzt nur den Entwurf zurück (Alle Termine, alle Kategorien).
- Anwenden übernimmt den Entwurf, schließt das Sheet und lädt neu. Der Filter-Button zeigt die Anzahl aktiver Filter als rosa Zähler.
- Schließen ohne Anwenden verwirft den Entwurf.

### R03-US8 · Leer- und Fehlerzustände
- **Keine Feste im Ausschnitt** (01-07): „Keine Feste in diesem Kartenausschnitt“, Aktionen „Herauszoomen“ (2 Stufen) und „Filter zurücksetzen“ (setzt Filter **und** Suche zurück).
- **Netzwerkfehler:** Toast „Feste konnten nicht geladen werden“ mit „Erneut versuchen“. Bereits geladene Marker bleiben stehen.
- **Offline:** Die zuletzt geladenen Feste bleiben aus dem persistierten Query-Cache lesbar (TanStack Query Persist, begrenzt auf die letzte Suche). Ein dezenter Hinweis „Offline · zuletzt geladen um {Zeit}“ erscheint (Annahme).

## Mobile-Struktur

- Screen `src/app/index.tsx` (Entdecken). Logik in `src/features/discover/`:
  - Store für `view`, `query`, `filter`, `mapCamera`, `selectedEventId` (State-Vorschlag aus der Design-Referenz)
  - Hooks `useEventSearch`, `useEventCount`, `useCategories` auf Basis der generierten Hooks
- Komponenten in `src/components/`, jeweils mit Story:
  - Suche und Filter: `SearchBar`, `FilterButton`, `Chip`, `ChipRow`, `FilterSheet`, `MonthGrid`, `RangeSlider`, `BottomSheet`
  - Karte: `EventMarker`, `ClusterMarker`, `SelectedPin`, `MapControls`, `LoadingPill`
  - Karten und Liste: `EventCarouselCard`, `EventListCard`, `SegmentedToggle`, `ImagePlaceholder`
  - Zustände und Profil: `EmptyState`, `AvatarButton`
- `testID`-Beispiele: `discover.search.input`, `discover.filter.open`, `discover.chip.<categoryId>`, `discover.toggle.list`, `discover.carousel.card.<eventId>`, `filter.apply`, `filter.reset`, `filter.radius`.

## Tests

- Jest: Status-Texte (laufend, ≤ 14 Tage, später, abgesagt, Tagesgrenzen), Filter-Entwurfslogik, Zählung aktiver Filter, stilles Entfernen unbekannter Kategorien.
- RNTL: Filter-Sheet (Entwurf, anwenden, zurücksetzen, 0 Treffer), Liste mit Leer- und Fehlerzustand.
- Maestro `guest-search.yaml`: App starten (Standort per Simulator gesetzt) → Chip wählen → Filter „Heute“ → Liste → Suche ohne Treffer → Filter zurücksetzen.

## Definition of Done

- [ ] Screens 01-01 bis 01-09 sind in dunkel und hell umgesetzt und mit den Screenshots abgeglichen.
- [ ] Alle neuen Komponenten haben Stories mit default/loading/empty/error.
- [ ] Der Maestro-Flow „Gastsuche“ läuft in `make test-e2e`.
- [ ] Das ADR zur Kartenkachel-Quelle liegt vor. Bei externem Anbieter gibt es ein Runbook und die Einordnung als EU-/Nicht-EU-Verarbeiter.

## Offene Punkte

- Kachelquelle (Protomaps selbst gehostet vs. MapTiler) → ADR.
- Performance ab mehreren tausend Markern im Ausschnitt: vorerst Limit 500 und Hinweis „Zoome hinein, um alle Feste zu sehen“ (Annahme).
