# Design-Referenz

> Typografie, Radien, Abstände, Bewegung und Screen-Beschreibungen im Detail. Die semantischen Farbrollen stehen in [theme-farben.md](theme-farben.md), die Abläufe in [../workflows/](../workflows/).

## Overview
Mobile App zum Entdecken von Stadtfesten, Volksfesten & Kirmes, Weihnachtsmärkten und Märkten in Deutschland. App-Sprache Deutsch, plattformneutral (iOS und Android). Drei Rollen:
- **Gast:** Karte, Liste, Suche, Filter, Detailseite, ohne Account voll nutzbar.
- **Angemeldeter Nutzer:** Favoriten, Teilen, Einladungen mit Zu-/Absage, gemeinsame Favoritenlisten, Benachrichtigungen und Einstellungen.
- **Moderator:** gleicher Account, eigene Moderator-Ansicht zum Pflegen von Festen (nur eigene Region) und app-weiten Kategorien sowie zum Anstoßen einer automatischen Fest-Suche per PLZ.

## About the Design Files
Die Dateien in diesem Paket sind **Design-Referenzen in HTML**. Es sind Prototypen, die Aussehen und Verhalten zeigen, kein Produktionscode zum Übernehmen. Aufgabe ist, diese Designs **in der Zielumgebung neu umzusetzen** (z. B. React Native/Expo, Flutter oder nativ SwiftUI + Jetpack Compose) mit deren Mustern und Bibliotheken. Gibt es noch keine Codebasis, empfiehlt sich wegen der Plattformneutralität **React Native (Expo)** oder **Flutter** mit einer Kartenbibliothek auf OpenStreetMap-Basis (MapLibre).

- `StadtfestFinder.dc.html` ist der voll klickbare Prototyp aller Flows. Er öffnet direkt im Browser, `support.js` muss daneben liegen. Die Property `start` (siehe unten) wählt den Startzustand, `theme` = `dunkel` | `hell`.
- `Stadtfest-Finder Richtungen.dc.html` ist das Canvas mit allen Screens und Zuständen nebeneinander: Runde 1 = verworfene Stilrichtungen, Runden 2–4 = finale Screens.

Logik und Daten stehen in der Klasse `Component` am Ende von `StadtfestFinder.dc.html`, das Markup im `<x-dc>`-Block. Alle Daten sind Beispieldaten, Backend-Aufrufe sind simuliert (setTimeout).

## Fidelity
**High-fidelity.** Farben, Typografie, Radien, Abstände, Zustände und Texte sind final gemeint. Bitte so genau wie möglich umsetzen. Fotos sind Platzhalter (gestreifte Flächen). Karten nutzen OSM-Kacheln, die im Dunkelmodus per CSS-Filter eingefärbt sind. In der echten App sollte stattdessen ein passender dunkler Vektor-Kartenstil verwendet werden.

Referenzgröße: **390 × 844 pt** (iPhone 14/15). Oben 44 pt Statusleiste, unten ca. 30 pt Home-Indicator-Zone. Alle Touch-Ziele ≥ 44 pt.

---

## Design Tokens

### Farben: Dunkelmodus (Standard)
| Token | Wert | Verwendung |
|---|---|---|
| bg | `#15111C` | App-Hintergrund |
| surface | `#231C30` | Karten, Listenzeilen |
| surface2 | `#2A2335` | Sekundär-Buttons, Chips (inaktiv, im Sheet), Pills |
| sheet | `#1D1727` | Bottom Sheets, Tab-Leiste (Moderator) |
| drawerBg | `#1B1624` | Profil-Drawer |
| line | `rgba(255,255,255,.09)` | Rahmen, Trenner |
| text | `#F4EEF8` | Primärtext |
| muted | `#A89BB8` | Sekundärtext |
| faint | `#6E6380` | Vergangene Einträge |
| chip | `rgba(35,28,48,.94)` | Schwebende Elemente über der Karte |
| glass | `rgba(21,17,28,.72)` | Runde Icon-Buttons über Bildern |
| scrim | `rgba(8,5,12,.6)` | Overlay hinter Sheets/Drawer |
| skel | `#2E2639` | Skeleton-Flächen |
| ph1 / ph2 | `#2C2438` / `#261F31` | Bild-Platzhalter-Streifen (135°, 10 px) |
| mapFilter | `invert(1) hue-rotate(180deg) brightness(.8) contrast(.9) saturate(.3) sepia(.12)` | nur Prototyp |
| meDot | `#60A5FA` | Eigener Standort |

### Farben: Hellmodus
| Token | Wert |
|---|---|
| bg | `#FBF8F4` |
| surface | `#FFFFFF` |
| surface2 | `#F1EBF3` |
| sheet / drawerBg | `#FFFFFF` |
| line | `rgba(35,26,46,.1)` |
| text | `#231A2E` |
| muted | `#6F6480` |
| faint | `#A79DB3` |
| accentText | `#A35A00` |
| accentSoft | `#FFF1DC` |
| roseText | `#C8284F` |
| roseSoft | `#FFE4EA` |
| glass | `rgba(255,255,255,.88)` |
| scrim | `rgba(20,12,28,.4)` |
| skel | `#EDE6EF` |
| ph1 / ph2 | `#EFE6F0` / `#E8DDEA` |
| meDot | `#2563EB` |

### Markenfarben (in beiden Modi gleich)
| Token | Wert | Verwendung |
|---|---|---|
| amber (Primär) | `#FFB547` | Primär-Buttons, aktive Chips, ausgewählter Pin, laufende Feste. Text darauf immer `#15111C` |
| rose (Zweitfarbe) | `#FF6B8B` | Cluster, Favoriten-Herz, Badges, „In X Tagen“, Fehler, Absagen |
| accentText dunkel | `#FFB547` | Amber als Textfarbe |
| accentSoft dunkel | `rgba(255,181,71,.13)` | Hervorgehobene Flächen (laufendes Fest) |
| roseText dunkel | `#FF6B8B` | |
| roseSoft dunkel | `rgba(255,107,139,.14)` | |
| Segment-Toggle dunkel | bg `#F4EEF8`, aktiv `#15111C` / Text `#F4EEF8` | Karte/Liste-Umschalter |
| Segment-Toggle hell | bg `#231A2E`, aktiv `#FFFFFF` / Text `#231A2E` | |
| Avatar Nutzer | `#4A3A5C` | |
| Freunde-Avatare | `#5B7FD6` `#C8508A` `#3E9A84` `#B07A2E` `#7B62D0` `#C85A3E` | |

### Moderator-Akzent (Türkis)
| Token | Dunkel | Hell |
|---|---|---|
| modBanner | `#0E3B38` | `#CCFBF1` |
| modText | `#5EEAD4` | `#0F766E` |
| modAccent (Buttons) | `#2DD4BF` | `#0F766E` |
| modOn (Text auf modAccent) | `#062321` | `#FFFFFF` |
| modSoft | `rgba(45,212,191,.14)` | `#DDF7F2` |

### Kategorie-Farben (von Moderatoren pflegbar)
Stadtfest `#FFB547` · Volksfest & Kirmes `#FF6B8B` · Weihnachtsmarkt `#5EEAD4` · Markt & Messe `#8B9CFF` · Weinfest (deaktiviert) `#C792EA`. Auswahlpalette: `#FFB547 #FF6B8B #5EEAD4 #8B9CFF #7ED957 #C792EA`. Die Kategorie-Farbe ist der **Rahmen der Karten-Marker** (2 px).

### Typografie
- **Display/Headlines:** *Young Serif* (Google Fonts), 400. Größen: 36 (Detail-Titel, lh 1.08), 32 (Login), 30 (Listen-Titel), 28 (Drawer-, Screen-Titel), 26, 24 (Sheet-Titel), 22, 21 (Abschnitt), 20 (Karten-Titel in Liste), 19, 18 (Karussell), 17, 16, 14 (Monatslabels der Zeitleiste).
- **UI/Fließtext:** *Outfit* (Google Fonts), 300–700. Body 15/1.5–1.6, Input 16, Buttons 15–17 / 600, Meta 13, Caption 12, Micro 11.
- **Abschnitts-Labels:** Outfit 13 / 600, `letter-spacing: .06em`, UPPERCASE, Farbe muted.
- Platzhalter-Beschriftung von Bildern: ui-monospace 10–11 / 500.

### Radien
Telefon 44 · Sheets oben 28 (Moderator-Sheets 24) · Karten 22 · Listen-/Info-Blöcke 18–20 · Primär-Buttons 16–18 · Inputs 14 · Chips 12–14 · Pills 9–12 · Icon-Buttons rund (50 %).

### Abstände
Seitenrand 16 (Drawer 20). Standardabstände 4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 22 / 24. Abstand zwischen Abschnitten auf Detail- und Formularseiten 22.

### Schatten
- Schwebende Elemente: dunkel `0 8px 24px rgba(0,0,0,.4)`, hell `0 6px 20px rgba(35,26,46,.14)`.
- Ausgewählter Pin: `0 0 28px rgba(255,181,71,.55)`. Cluster: `0 0 0 7px rgba(255,107,139,.25), 0 0 24px rgba(255,107,139,.5)`.
- Toast: `0 10px 30px rgba(0,0,0,.3)`.

### Bewegung
- Seiten (Detail, Unterseiten) schieben von rechts herein: `transform translateX(100%→0)`, **340 ms `cubic-bezier(.2,.8,.2,1)`**.
- Sheets schieben von unten herein (`translateY 105%→0`), 340 ms, gleiche Kurve. Scrim-Deckkraft ändert sich in 300 ms.
- Drawer von rechts, Breite 336, 340 ms.
- Login-Vollbild von unten, 380 ms.
- Toast: 250 ms Einblenden plus 12 px nach oben, nach 2,2 s automatisch weg.
- Skeleton: Pulsieren der Deckkraft .55↔1, 1,2 s. Spinner: 16 px, 2 px Rand, 0,8 s linear.

---

## Screens / Views

Die Klammer nennt jeweils den `start`-Wert im Prototyp.

### 1. Kartenansicht / Startseite (`karte`)
- Vollflächige Karte (OSM), verschieb- und zoombar (Zoom 6–13), Start etwa bei 48.85°N, 10.95°E, Zoom 8.
- **Header** schwebt transparent über der Karte, beginnt 52 pt unter der Oberkante:
  - Suchfeld (Höhe 50, Radius 16, Hintergrund `chip`, 1 px `line`). Darin Lupe in Amber, Platzhalter „Fest oder Ort suchen“, ✕ zum Leeren sowie der Filter-Button (40 × 40) mit rosa Zähler für aktive Filter.
  - Profilbild daneben: 50 pt, Ring 2 px Amber. Initialen, Gast-Icon oder roter Punkt für ungelesene Benachrichtigungen.
- **Chip-Reihe** 12 pt darunter, horizontal scrollbar (Wischen, Mausrad, Ziehen). Scrollleiste ausblenden. Ein Ziehen darf keinen Chip auslösen.
  - Zuerst der Zeitraum-Chip mit ▾, er öffnet das Filter-Sheet.
  - Danach die Kategorie-Chips „{Emoji} {Name} {Anzahl}“, Höhe 36, Radius 12.
  - Aktiv: Amber-Hintergrund, Text `#15111C`.
- **Marker:**
  - Einzelmarker: 38 pt Kreis, `surface2`, Rahmen 2 px in der Kategorie-Farbe, Emoji 17 pt.
  - Ausgewählter Marker: Amber-Pille (Höhe 56), links oder rechts ausgerichtet, je nachdem auf welcher Bildschirmhälfte er liegt, mit Kurznamen und darunter dem Zeitraum (z. B. „3.–4. Okt“). Er ist **nie Teil eines Clusters** und liegt über allen anderen Markern.
  - Cluster: 44 pt Kreis in Rosa mit Zahl. Marker unter 46 px Abstand werden gruppiert. Ein Tipp auf den Cluster zoomt 2 Stufen hinein. Lässt er sich auch beim größten Zoom nicht auflösen (Feste am selben Ort), zeigt ein Bottom Sheet „{n} Feste an diesem Ort“ die Feste als Liste.
  - Eigener Standort: 14 pt blauer Punkt mit Ring.
- **Kartensteuerung** rechts, 236 pt über dem unteren Rand: +/− (48 × 44 je Taste) und Standort-Button (48 × 48, Radius 16).
- ~~**Karussell**~~ entfällt (Entscheidung 01.10.2026): Es nahm zu viel Platz von der Karte. Die Informationen zum ausgewählten Fest zeigt der ausgewählte Marker selbst (Name und Zeitraum), alles Weitere die Detailseite. Kartensteuerung und Attribution sitzen direkt über dem Karte/Liste-Umschalter.
- **Karte/Liste-Umschalter** unten mittig, 36 pt über dem Rand. Segmented Control mit Radius 24, zwei Segmenten à 40 pt Höhe mit Icon und Text („Karte“ / „Liste“).
- **Tipp-Logik:** Der erste Tipp auf einen Marker wählt ihn aus (Pille mit Name und Zeitraum), der zweite öffnet die Detailseite. Ein Tipp auf die Karte hebt die Auswahl auf.

### 2. Listenansicht (`liste`)
- Gleicher Header, hier mit deckendem `bg` und unterer Linie.
- Überschrift „{n} Feste im Kartenausschnitt“ (Serif 22) und rechts „nach Datum“, darunter „um {Ort}“ und „Ausschnitt ändern“ (Entscheidung 29.09.2026: Kartenausschnitt statt Umkreis).
- Karten: Bild 160 hoch. Oben links das Badge „● Läuft gerade“ (Amber), oben rechts der Herz-Button (40, `glass`). Darunter Status, Name (Serif 20), „{Zeitraum} · {Ort}“ sowie die Pills für Kategorie und Entfernung.
- Such- und Filterzustand bleibt beim Wechsel zwischen Karte und Liste erhalten.

### 3. Filter (Bottom Sheet) (`filter`)
- Griff (40 × 5), Titel „Filter“ (Serif 24) und ✕.
- **Zeitraum:** Chips „Alle Termine“, „Heute“, „Dieses Wochenende“, „Zeitraum wählen“. Bei der letzten Option erscheint ein Raster mit 4 Monaten (Mehrfachauswahl).
- **Kategorie:** Chips mit Mehrfachauswahl, nur aktive Kategorien in der Reihenfolge der Moderation.
- ~~Entfernung~~: entfällt, eingegrenzt wird durch Zoomen der Karte (Entscheidung 29.09.2026).
- Fußzeile: „Zurücksetzen“ (unterstrichen) und Primär-Button „{n} Feste anzeigen“ mit Live-Zählung. Bei 0 Treffern lautet er „Keine Treffer – trotzdem anwenden“.
- Filter werden als Entwurf bearbeitet und erst mit „anwenden“ übernommen.

### 4. Detailseite (`detail`)
- **Galerie** 340 hoch: Tipp auf die linke oder rechte Hälfte blättert, Punkte zeigen die Position (aktiv 18 × 5 Amber, sonst 6 × 5), Zähler „1 / 6“.
- Oben schweben Zurück, Teilen und Herz (je 44, `glass`).
- Der Inhaltsblock überlappt die Galerie um 28 pt (Radius 28 oben):
  - Pills für Kategorie und Status, Titel (Serif 36), „{Ort}, {Stadt} · {km} km entfernt“.
  - Bei Einladungen der Hinweis „Jonas und Tim kommen mit“ mit Avataren.
- **Infoblock** (`surface`, Radius 20): Zeitraum, Öffnungszeiten (mehrzeilig), Eintritt, jeweils mit Icon-Kachel 36 in `accentSoft`.
- Abschnitte mit Serif-21-Überschriften: „Über das Fest“, „Programm & Highlights“, „Ort“, „Anfahrt“.
  - Programm: Zeilen mit Wochentag und Datum in Rosa, Titel und Untertitel.
  - Ort: Mini-Karte 160 hoch mit zentriertem Amber-Pin und Adresse. Ein Tipp startet die Route.
  - Anfahrt: getrennte Angaben zu ÖPNV und Parken.
- Zeile „Offizielle Website ↗“.
- **Fixe Fußleiste:** „Route starten“ (Amber, Höhe 54, flex 1) und „Einladen“ (`surface2`).
- **Status „Abgesagt“:** rote Pill auf `roseSoft`.

### 5. Hinweis „Anmelden für diese Funktion“ (Gast) (`gasthinweis`)
- Bottom Sheet, das nichts blockiert. Icon-Kachel 56 in `roseSoft` (Herz oder Personen je nach Auslöser), Titel (Serif 24), Text.
- Buttons „Anmelden oder registrieren“ (Amber) und „Weiter ohne Konto“.
- Texte je Auslöser:
  - Favorit: „Lieblingsfeste merken“ / „Mit einem kostenlosen Konto speicherst du Favoriten auf deiner Zeitleiste und wirst vor Festbeginn erinnert.“
  - ~~Teilen~~: entfällt, Teilen geht ohne Konto (Entscheidung 29.09.2026).
  - Einladen: „Freunde einladen“ / „Mit einem Konto lädst du Freunde ein und siehst, wer zu- oder abgesagt hat.“
- Nach der Anmeldung wird die ausgelöste Aktion nachgeholt (z. B. das Fest gemerkt, Toast „Angemeldet · Fest gemerkt“).

### 6. Login / Registrierung (`login`)
- Vollbild von unten. Titel „Willkommen zurück“ bzw. „Konto erstellen“, darunter „Favoriten, Einladungen und Erinnerungen an einem Ort.“
- Segment „Anmelden | Registrieren“.
- „Mit Apple fortfahren“ (dunkel: heller Button, hell: dunkler Button), „Mit Google fortfahren“ und der Trenner „oder mit E-Mail“.
- Bei Registrierung Vorname und Nachname nebeneinander, dann E-Mail und Passwort. „Passwort vergessen?“ nur im Anmelden-Modus.
- **Validierung:** E-Mail nach Muster `\S+@\S+\.\S+`, sonst „Bitte gib eine gültige E-Mail-Adresse ein.“. Passwort mindestens 8 Zeichen, sonst „Das Passwort braucht mindestens 8 Zeichen.“. Fehler: Rand `#FF6B8B`, Text darunter in `roseText`.
- Senden-Button mit Spinner und „Einen Moment …“.
- Rechtshinweis unten (12 pt).

### 7. Profil-Drawer (`drawer`, `drawer-vergangen`, `drawer-gast`, `drawer-leer`)
- Fährt von rechts ein, 336 breit, Scrim dahinter.
- **Nutzer-Zeile** bewusst dezent (Deckkraft .85): Avatar 32, Name 14, E-Mail 12, dazu ✕.
- **„Gemeinsame Listen“** als kompakte Karte über der Zeitleiste: 3 überlappende Avatare, Titel und „{n} Listen · {Namen}“.
- **Hauptelement:** „Deine Festsaison“ (Serif 28) mit „{n} Favoriten stehen an“ und dem Button „↑ Vergangene einblenden ({n})“, der danach zu „↓ Vergangene ausblenden“ wechselt.
- **Zeitleiste:**
  - Vertikale Linie 2 px bei x = 5, Einträge 24 pt eingerückt, gruppiert nach Monat (Serif 14, Rosa).
  - Normale Einträge: Punkt 10 pt mit rosa Rand, Datum, Name (Serif 17), „{Emoji} {Kategorie} · {Ort}“.
  - **Laufendes Fest:** Karte in `accentSoft` mit Amber-Rand, leuchtendem Punkt 14 und „● Läuft · noch X Tage“.
  - **Vergangene** Einträge stehen oberhalb, ausgegraut (`faint`), und enden mit dem Trenner „HEUTE · FR 25.09.“ in Rosa.
  - Ein Tipp öffnet die Detailseite.
- **Leerer Zustand:** gestrichelte Box mit Herz-Icon, „Noch keine Favoriten“, Erklärung und Button „Feste entdecken“.
- **Gast-Variante:** „Deine Festsaison auf einen Blick“ mit Nutzen-Text, angedeuteter Zeitleiste (Skeleton, Deckkraft .5), Login-Button und „Alle Feste kannst du auch ohne Konto entdecken.“
- **Fußbereich** mit Trennlinie: Schalter Dunkelmodus, „Benachrichtigungen“ mit rosa Zähler, „Moderator-Ansicht“ (nur für Moderatoren, in Amber) und „Abmelden“ (in Rosa).

### 8. Gemeinsame Favoritenlisten (`listen`, `liste-detail`, `liste-bearbeiten`)
- **Übersicht:** Zurück, Titel „Gemeinsame Listen“, Button „+ Neu“. Hinweis „Plant Festbesuche zusammen. …“. Karten zeigen Name, Anzahl der Feste, Avatare, „{n} Personen“ und das nächste Fest.
- **„+ Neu“:** Sheet mit Namensfeld und Freundesauswahl (Häkchen). „Liste erstellen“ ist erst nach Eingabe eines Namens aktiv.
- **Liste:**
  - Titel (Serif 30).
  - Mitglieder als Avatare 48 in einer horizontalen Reihe, dazu „+ Hinzufügen“.
  - „Feste · chronologisch“ mit Datumsblock (Tag in Rosa, Monat) und „+ Fest hinzufügen“ (Sheet mit Mehrfachauswahl).
  - Vergangene Feste mit Deckkraft .5.
- **Bearbeiten-Modus:** Button „Fertig“ in Amber, Name als Eingabefeld, ✕ zum Entfernen von Mitgliedern und Festen, dazu „Liste löschen“ (Rosa). Alle Mitglieder dürfen die Liste bearbeiten.

### 9. Einladung (`einladung`, `einladung-neu`, `einladung-erhalten`)
- **Übersicht (Einladender):**
  - Kopf mit Bild 56 und Fest.
  - 3 Zählerkacheln: „kommen“ (Amber), „offen“, „abgesagt“ (Rosa).
  - Nachricht als Sprechblase.
  - Gruppen „Kommen mit“ / „Noch keine Antwort“ / „Abgesagt“ mit Pills.
  - Fußleiste: „Erinnern“ und „Weitere einladen“.
- **Verfassen:** Freunde-Liste mit Häkchen (bereits Eingeladene werden ausgeblendet), Nachricht (optional) und „Freunde ohne App? Link teilen ↗“. Der Button lautet „Einladung senden ({n})“ und ist ohne Auswahl deaktiviert.
- **Erhalten:** „{Name} lädt dich ein“, Nachricht, Fest-Karte, „Ebenfalls eingeladen“ mit Status, Buttons „Absagen“ und „Zusagen“ (Amber, flex 1.4). Nach der Antwort erscheint ein Banner „✓ Du hast zugesagt“ bzw. „Du hast abgesagt“ mit „Ändern“. Eine Zusage merkt das Fest automatisch als Favorit.

### 10. Benachrichtigungen und Einstellungen (`benachrichtigungen`, `benachrichtigungs-einstellungen`)
- **Liste:** Gruppen „Neu“ / „Früher“ und „Alle als gelesen markieren“. Einträge haben eine Icon-Kachel 40, eine Art-Zeile, Text (ungelesen fett auf `surface`) und Zeit. Ungelesene tragen einen rosa Punkt. Ein Tipp führt zum Ziel (Detailseite, Einladung, Zu-/Absage).
  - Arten: Einladung ✉️, Zusage 👍, Absage 👋, Erinnerung ⏰, „Neu an deinem Wohnort“ 📍, Änderung ✏️, „Fest abgesagt“ ⚠️ (Rosa).
- **Einstellungen:** Jede Art ist einzeln schaltbar (Switch 48 × 28, an = Amber).
  - Erinnerungen an Favoriten: Zeitpunkt „1 Tag vorher | 3 Tage | 1 Woche“.
  - Neue Feste an deinem Wohnort: **Wohnort** per Stadt oder PLZ mit Vorschlagsliste, alternativ „Aktuellen Standort verwenden“. Dazu der **Radius** 5–150 km in 5er-Schritten (Standard 25) und eine Vorschau „Aktuell {n} Feste im Umkreis von {r} km um {Ort}. …“.
  - Änderungen und Absagen, Einladungen, Zu- und Absagen.

### 11. Moderator: Übersicht der Feste (`mod-feste`)
- **Klar abgegrenzt:** Türkis statt Amber. Festes Banner oben in `modBanner` mit Schild-Icon, „MODERATOR-ANSICHT“ (11 / 700, Laufweite .1em), „Region Ostalb · {Name}“ und dem umrandeten Button „Beenden“. Unten eine eigene Tab-Leiste „📅 Feste | 🏷️ Kategorien“ (aktiver Tab: Pille in `modSoft`).
- Titel „Feste“, Buttons „Suchen“ (umrandet, öffnet die PLZ-Suche, siehe 11a) und „+ Neues Fest“.
- Suchfeld „Fest oder Ort in deiner Region“.
- Status-Chips mit Anzahl: Alle / Entwurf / Veröffentlicht / Vergangen / Abgesagt.
- Zeilen: Datumsblock, Name (abgesagte durchgestrichen), „{Emoji} {Ort} · {Zeitraum}“, Status-Pill, ggf. „Automatisch gefunden“ und „♥ {Favoriten}“. Vergangene haben Deckkraft .6.
- Sortierung: anstehende aufsteigend, danach vergangene absteigend.
- Status „Vergangen“ wird automatisch vergeben, sobald das Ende eines veröffentlichten Fests vor heute liegt.
- Ladezustand mit Skeleton, leerer Zustand „Keine Feste gefunden“.

### 11a. Moderator: Automatische Fest-Suche per PLZ (`mod-import`, `mod-import-ergebnis`, `mod-pruefen`)
Die Suche selbst ist ein **Backend-Dienst**. Er bekommt nur eine PLZ, ein KI-Dienst sucht online nach Veranstaltungen und legt Funde als **Entwurf** an. Das Frontend löst die Suche nur aus und zeigt Status und Ergebnis an.
- **Sheet** „Feste automatisch suchen“: kurze Erklärung und ein PLZ-Feld (nur Ziffern, genau 5, Schrift 22 / 600, Laufweite .12em). Bei einer bekannten PLZ steht der Ort darunter. „Suche starten“ ist nur bei gültiger Eingabe aktiv. Fehlertext: „Bitte gib eine fünfstellige Postleitzahl ein.“
- **Während der Suche:** Leiste in `modSoft` mit Spinner, „Suche läuft für {PLZ} {Ort} …“.
- **Danach:** Leiste „{n} neue Entwürfe aus der Suche für {PLZ}“ mit „Prüfen“ und ✕. Funde tragen die Pill „Automatisch gefunden“.
- **Prüfmodus:** Die Funde erscheinen der Reihe nach, oben ein Fortschritt aus Segmenten (Türkis = erledigt, Rosa = verworfen). Pro Fund:
  - Bild oder „Kein Bild gefunden“, Name, Kategorie, Zeitraum, Adresse.
  - Kasten „Gefunden auf {Quelle}“ mit „Öffnen ↗“.
  - Tabelle der Angaben, fehlende in Rosa als „fehlt“, dazu ein Hinweis.
  - Aktionen:
    - „Verwerfen“ löscht den Entwurf.
    - „Bearbeiten“ öffnet das Formular 12. Nach dem Speichern geht es zum nächsten Fund.
    - „Veröffentlichen“ schaltet das Fest frei. Fehlt eine Pflichtangabe, öffnet sich stattdessen das Formular.
  - ✕ pausiert, offene Funde bleiben Entwürfe.
  - Zum Schluss: „Alle Funde geprüft“ mit Zusammenfassung und „Zur Übersicht“.

### 12. Moderator: Fest anlegen / bearbeiten (`mod-fest-bearbeiten`, `mod-fest-neu`, `mod-absagen`)
- **Kopf:** Zurück, Titel und „Status: …“. Bei bestehenden Festen zusätzlich ein „⋯“-Menü (Sheet mit „⚠️ Fest absagen“, nur bei veröffentlichten, und „🗑️ Fest löschen“).
- **Felder** (Label-Stil siehe Tokens, Pflichtfelder mit *):
  - Name *
  - Kategorie * (Chips, aktive Kategorien)
  - Zeitraum * (Beginn und Ende als Datumsfelder)
  - Öffnungszeiten (Textarea)
  - Ort *: Segment „Adresse | Pin auf Karte“, Adressfeld und Karte 180 hoch mit Pin in `modAccent`. Im Pin-Modus setzt ein Tipp auf die Karte den Pin (Karte bekommt dabei einen Türkis-Rand, Hinweis „Tippe, um den Pin zu setzen“). Ohne Adresse wird „Pin {lat}, {lon}“ eingetragen.
  - Beschreibung
  - Programm (Zeilen „Tag, Zeit“ 112 breit und „Programmpunkt“, ✕, gestrichelter Button „+ Programmpunkt“)
  - Eintritt
  - Anfahrt (ÖPNV, Parken)
  - Website
  - Bilder (Raster mit 3 Spalten, erstes Bild = „Titelbild“, ✕ zum Entfernen, Kachel „+ Hochladen“ mit Spinner „Lädt hoch“)
- **Fußleiste:** „Als Entwurf“ und „Veröffentlichen“ bzw. „Änderungen veröffentlichen“.
- **Validierung:**
  - Entwurf: nur der Name ist Pflicht.
  - Veröffentlichen: Name, Kategorie, Beginn, Ende und Adresse/Pin. Das Ende darf nicht vor dem Beginn liegen („Das Ende liegt vor dem Beginn.“). Zusätzlich Toast „Bitte fülle die markierten Pflichtfelder aus“.
- **Absagen:** Dialog „Fest absagen?“ mit „{n} Nutzer mit diesem Favoriten werden benachrichtigt.“, optionalem Grund (Textarea) und „Absagen und benachrichtigen“ (Rosa).
- **Löschen:** Dialog mit „Endgültig löschen“. Hat das Fest Favoriten, weist der Dialog darauf hin, dass die Nutzer bei Löschung nicht benachrichtigt werden und Absagen die bessere Wahl ist.

### 13. Moderator: Kategorien verwalten (`mod-kategorien`)
- Titel und „+ Neu“, Erklärung.
- **Vorschau Startseite:** die aktiven Chips in der aktuellen Reihenfolge.
- Zeilen 64 hoch, Abstand 72:
  - **Griff** (6 Punkte, 40 × 56) für Drag & Drop: Pointer Capture, andere Zeilen rücken mit `top .2s` nach, die gezogene Zeile bekommt Schatten und Türkis-Rand.
  - Emoji-Kreis 40 mit Kategorie-Farbe (Rand und Farbe mit 16 % Deckkraft als Hintergrund), Name und „{n} Feste“ bzw. „Deaktiviert · {n} Feste“ (Zeile mit Deckkraft .5).
- Beim Loslassen wird die Reihenfolge gespeichert, Toast „Reihenfolge gespeichert · Chips auf der Startseite aktualisiert“.

### 14. Moderator: Kategorie anlegen / bearbeiten (`mod-kategorie-bearbeiten`, `mod-kategorie-loeschen`)
- **Vorschau:** Chip und Karten-Marker in der gewählten Farbe.
- Name *, Emoji-Raster mit 6 Spalten und 12 Emojis (🎪 🎡 🎄 🐎 🍺 🍷 🎭 🎶 🏰 🎃 🌸 🔥), Farbe (6 Kreise à 44, Auswahl mit doppeltem Ring).
- Schalter „Aktiv“: Deaktivierte Kategorien erscheinen nicht als Filter-Chip, zugeordnete Feste bleiben erhalten.
- „Kategorie löschen“ öffnet einen Dialog:
  - Ohne Feste: einfache Bestätigung.
  - **Mit Festen:** Pflicht-Auswahl einer **Ersatzkategorie** (Radio-Liste). Bis dahin ist der Button deaktiviert („Ersatz wählen“), danach heißt er „Löschen und verschieben“ und verschiebt die Feste in die Ersatzkategorie.

---

## Interactions & Behavior (übergreifend)
- **Navigation:** Unterseiten liegen als Stapel übereinander. Die zuletzt geöffnete liegt oben, die Zurück-Taste schließt nur die oberste.
- **Toasts** bestätigen jede Aktion (Texte stehen im Prototyp).
- **Teilen:** in der App das native Share-Sheet, auch für Gäste, mit dem Link `https://stadtfest.herderstreet.de/f/{id}` (Host per `EXPO_PUBLIC_LINK_HOST`). Im Prototyp erscheint ein Toast.
- **„Route starten“:** öffnet die Standard-Karten-App (Apple Maps / Google Maps).
- **Laden:** Skeleton-Karten im Karussell und in der Liste, Pille „Feste werden geladen …“ auf der Karte. Nach jeder Filteränderung wird neu geladen.
- **Leere Zustände:**
  - Keine Feste im Ausschnitt: „Keine Feste in diesem Kartenausschnitt“ mit „Herauszoomen“ und „Filter zurücksetzen“.
  - Suche ohne Treffer: „Kein Fest für ‚{q}‘“.
  - Außerdem: noch keine Favoriten, keine Listen, keine Feste in einer Liste, Moderator-Suche ohne Treffer.
- **Moderation wirkt sofort auf die App:**
  - Veröffentlichte Feste erscheinen in Karte, Liste und auf der Detailseite. Entwürfe und gelöschte Feste bleiben unsichtbar.
  - Abgesagte Feste bleiben sichtbar mit dem Status „Abgesagt“.
  - Kategorien: Reihenfolge und Aktiv-Status bestimmen die Filter-Chips, die Farbe den Marker-Rand.
- **Push-Auslöser (Backend):**
  - Absage eines Fests → alle Nutzer mit diesem Favoriten.
  - Änderung an einem Favoriten → Änderungsmeldung.
  - Neues veröffentlichtes Fest im Radius um den Wohnort → „Neu an deinem Wohnort“, wenn aktiviert.
  - Erinnerung X Tage vor einem Favoriten.
  - Einladung sowie Zu-/Absage.
- **Dunkel-/Hellmodus:** Standard ist dunkel, umschaltbar im Drawer. In der echten App der Systemeinstellung folgen und im Drawer überschreibbar machen.

## State Management (Vorschlag)
- **Entdecken:** `view` (map|list), `query`, `filter {time: alle|heute|wochenende|zeitraum, months[], cats[], radius}`, `mapCamera {center, zoom}`, `selectedEventId`, `loading`.
- **Auth:** `user {first, last, email, roles[], region}` oder `null`, dazu `pendingAction` (wird nach dem Login nachgeholt).
- **Nutzerdaten:** `favorites[]`, `sharedLists[] {id, name, members[], events[]}`, `invitations {eventId: {members[{userId, status: ja|offen|nein}], message}}`, `receivedInvites[]`, `notifications[] {type, text, time, unread, target}`.
- **Einstellungen:** `notificationSettings {remind, remindDaysBefore: 1|3|7, near, home {name, plz, lat, lon}, nearRadiusKm, change, invite, rsvp}`, `theme`.
- **Moderation:** `modEvents[] {…Fest, status: draft|pub|cancel, favCount, source?, autoFound?}` (Status „Vergangen“ wird abgeleitet), `categories[] {id, name, emoji, color, active, order}`, `aiSearchJob {plz, state: running|done, newIds[]}`, `reviewQueue {ids[], index, results}`.
- **API (Annahme):** `GET /events?bbox&from&to&cats&radius&q`, `GET /events/:id`, `POST/DELETE /favorites/:id`, `GET/POST/PATCH /lists`, `POST /events/:id/invitations`, `PATCH /invitations/:id {status}`, `GET /notifications`, `PATCH /me/notification-settings`. Moderation: `GET/POST/PATCH/DELETE /mod/events` (auf die Region beschränkt), `POST /mod/events/:id/cancel {reason}`, `GET/POST/PATCH/DELETE /categories` (Löschen mit `replacementId`), `PATCH /categories/order`, `POST /mod/ai-search {plz}` → Job-ID, Status per Polling oder Push.

## Assets
- **Schriften:** Young Serif, Outfit (Google Fonts, OFL).
- **Icons:** einfache Outline-SVGs, im Prototyp inline gezeichnet (Stroke 2–2,2, round caps). Bitte durch die Icon-Bibliothek der Codebasis ersetzen (z. B. Lucide, SF Symbols / Material Symbols).
- **Kategorie- und Benachrichtigungssymbole:** System-Emoji.
- **Karten:** OpenStreetMap-Kacheln (© OpenStreetMap-Mitwirkende). Für die Produktion eigene bzw. lizenzierte Vektor-Kacheln mit hellem und dunklem Stil verwenden.
- **Fotos:** nur Platzhalter, echte Bilder kommen von Moderatoren bzw. aus der KI-Suche.

## Prototyp

`../prototyp/StadtfestFinder-Prototyp.html` öffnen (Doppelklick). Alle Zustände der Screenshots sind im Prototyp über den `start`-Wert aus dem [Screen-Inventar](../00-ueberblick/screen-inventar.md) erreichbar.
