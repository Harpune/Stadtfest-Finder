# MapTiler Cloud einrichten

## Zweck

Vektorkacheln und Kartenstile (dunkel/hell) für die Karte der App ([ADR 0009](../25-adr/0009-kartenkacheln-maptiler.md), R03).

## Voraussetzungen

- Ein MapTiler-Konto (https://cloud.maptiler.com), für den Produktivbetrieb ein Tarif passend zur erwarteten Nutzung
- Die Bundle-ID bzw. Paketname der App: `de.stadtfestfinder.app`
- Zugriff auf die EAS-Secrets bzw. die lokale `mobile/.env`

## Schritte

1. **Konto anlegen** bzw. anmelden. Unter *Account → Settings* die Rechnungsadresse hinterlegen und den **AV-Vertrag (DPA)** von MapTiler abschließen bzw. akzeptieren. Standort der Datenverarbeitung prüfen und im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) nachtragen.
2. **API-Schlüssel anlegen:** *Account → API keys → New key*, Name z. B. `stadtfest-app-prod`. Für Entwicklung einen eigenen Schlüssel `stadtfest-app-dev` anlegen.
3. **Schlüssel einschränken:**
   - Den Prod-Schlüssel auf die benötigten Dienste (Maps/Tiles) beschränken.
   - Keine User-Agent- oder Origin-Beschränkung setzen: Die App sendet keinen eigenen User-Agent, und jeder Client kann diese Werte ohnehin frei setzen. Ein mobiler Schlüssel ist nie geheim. Stattdessen die Nutzung im Dashboard beobachten und den Schlüssel bei Missbrauch rotieren.
4. **Stile prüfen:** Die App nutzt standardmäßig `streets-v2-dark` und `streets-v2`. Andere Stile (auch eigene aus dem MapTiler-Editor) über ihre ID setzen.
5. **Schlüssel hinterlegen** (nie ins Repo):
   - Lokal in `mobile/.env`:
     ```bash
     EXPO_PUBLIC_MAPTILER_KEY=<dev-key>
     # optional:
     EXPO_PUBLIC_MAPTILER_STYLE_DARK=streets-v2-dark
     EXPO_PUBLIC_MAPTILER_STYLE_LIGHT=streets-v2
     ```
   - Für Builds als EAS-Secret `EXPO_PUBLIC_MAPTILER_KEY` (Einrichtung der EAS-Builds folgt in R16).
6. Metro bzw. den Build neu starten, damit die Variable übernommen wird.

## Prüfung

- Die App zeigt eine Karte mit Straßen und **deutschen** Ortsnamen (z. B. „Sachsen“, „Bayern“), im Dunkelmodus dunkel, im Hellmodus hell.
- Schlüssel prüfen, ohne ihn auszugeben: `curl -s -o /dev/null -w "%{http_code}" "https://api.maptiler.com/maps/streets-v2/style.json?key=$KEY"` liefert `200`.
- Unten links steht die Attribution „© MapTiler © OpenStreetMap-Mitwirkende“.
- Im MapTiler-Dashboard (*Analytics*) erscheinen Abrufe für den Schlüssel.
- Ohne Schlüssel zeigt die App nur den Hintergrund mit Markern (Offline-Stil), das ist gewollt.

## Rollback

- Schlüssel im MapTiler-Konto deaktivieren bzw. rotieren und neu hinterlegen.
- Zurück auf den Offline-Stil: `EXPO_PUBLIC_MAPTILER_KEY` leeren.
- Wechsel des Anbieters (z. B. Protomaps): neue Style-URL in `mobile/src/features/discover/mapStyle.ts` plus neues ADR.
