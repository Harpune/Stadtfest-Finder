# 0009 · Kartenkacheln von MapTiler Cloud

- **Status:** angenommen
- **Datum:** 2026-09-29

## Kontext

Die Karte (R03) braucht OSM-basierte Vektorkacheln mit einem dunklen und einem hellen Stil. Die App lädt die Kacheln direkt vom Kachel-Server, nicht über das Backend. Zur Wahl standen:
- selbst gehostete Protomaps-PMTiles im eigenen Objektspeicher,
- der Kachel-Dienst MapTiler Cloud.

## Entscheidung

- **MapTiler Cloud** (MapTiler AG, Zug, Schweiz) liefert Vektorkacheln und Kartenstile.
- Die App lädt einen **Stil pro Farbschema** über die Style-URL:
  - dunkel: Standard `streets-v2-dark`
  - hell: Standard `streets-v2`
  - Beide IDs lassen sich per ENV ändern (`EXPO_PUBLIC_MAPTILER_STYLE_DARK`, `EXPO_PUBLIC_MAPTILER_STYLE_LIGHT`).
- Der **API-Schlüssel** kommt aus `EXPO_PUBLIC_MAPTILER_KEY`. Er ist ein öffentlicher Client-Schlüssel und steckt zwangsläufig im App-Bundle. Er wird deshalb im MapTiler-Konto eingeschränkt, siehe Runbook.
- **Ohne Schlüssel** (lokale Entwicklung, Tests, Storybook) nutzt die App einen eingebauten Offline-Stil nur mit Hintergrundfarbe. Marker, Cluster und Auswahl funktionieren weiter, es wird kein externer Dienst angefragt.
- Die Attribution „© MapTiler © OpenStreetMap-Mitwirkende“ bleibt sichtbar (Pflicht laut MapTiler- und OSM-Lizenz).

## Datenschutz

- MapTiler ist ein **Auftragsverarbeiter**. Bei jedem Kachelabruf sieht er die **IP-Adresse** des Geräts und die abgerufenen Kacheln. Die Kacheln zeigen ungefähr den betrachteten Kartenausschnitt und damit oft die Umgebung des Nutzers.
- Die Schweiz hat einen Angemessenheitsbeschluss der EU-Kommission (2000/518/EG). Ein AV-Vertrag mit MapTiler ist vor dem Produktivstart abzuschließen. Wo MapTiler die Daten hostet (Rechenzentren, CDN), ist dabei zu prüfen und im Verarbeiterverzeichnis nachzutragen.
- Die eigene Standortposition geht **nie** an MapTiler. Sie wird nur auf dem Gerät gezeichnet.
- Einträge: [Verarbeitungsverzeichnis Nr. 4](../30-privacy/verarbeitungsverzeichnis.md), [Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md).

## Konsequenzen

- Schneller Start mit fertigen Stilen, kein eigener Kachel-Build.
- Laufende Kosten ab der Nutzungsgrenze des Free-Tarifs. Die Nutzung ist im MapTiler-Konto zu beobachten.
- Wechselt man später auf Protomaps, reicht eine andere Style-URL; der Code greift nur über `features/discover/mapStyle.ts` darauf zu.

## Verworfene Alternativen

- **Protomaps selbst gehostet:** kein Dritter und kein Schlüssel, aber ein eigener Kachel-Build bzw. monatlicher Download (Deutschland ≈ 2–3 GB), eigene dunkle und helle Stile und Last auf dem Heimserver. Bleibt die Option, falls Kosten oder Datenschutz das erfordern.
- **OSM-Rasterkacheln (tile.openstreetmap.org):** laut Nutzungsrichtlinie nicht für Apps mit nennenswerter Last erlaubt, keine Vektorstile.
