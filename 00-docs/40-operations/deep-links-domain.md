# Deep Links und Domain einrichten

## Zweck

Links wie `https://stadtfest.herderstreet.de/f/{eventId}` öffnen die Detailseite in der App (R04-US6), Freundschaftslinks `https://stadtfest.herderstreet.de/freund/{token}` das Annehmen der Freundschaft (R12), Einladungslinks `…/e/{token}` die Einladungsvorschau und `…/einladung/{invitationId}` eine erhaltene Einladung (R14). Ohne installierte App zeigt die Domain eine einfache Seite. Zusätzlich funktioniert immer das App-Schema `stadtfest://f/{eventId}`, `stadtfest://freund/{token}`, `stadtfest://e/{token}` bzw. `stadtfest://einladung/{invitationId}`.

**Domain konfigurierbar:** `EXPO_PUBLIC_LINK_HOST` (Standard `stadtfest.herderstreet.de`) bestimmt den Host der geteilten Links und des Android-Intent-Filters (`mobile/app.config.ts`). Für App Links wirkt eine Änderung erst mit einem neuen Build. Caddy liest denselben Wert aus `LINK_HOST`.

**Stand:** Android App Links sind konfiguriert. iOS Universal Links folgen, sobald ein Apple-Developer-Konto mit Team-ID vorhanden ist (siehe unten).

## Voraussetzungen

- DNS-Zugriff für `herderstreet.de`
- Ein Webserver mit TLS für `stadtfest.herderstreet.de`, vorgesehen: Caddy auf dem Heimserver (Stack in R16, Konfiguration `infra/deeplinks/Caddyfile`)
- Der SHA-256-Fingerabdruck des Android-Signaturschlüssels:
  - Release: aus EAS (`npx eas-cli@latest credentials -p android` → *Keystore* → *SHA256 Fingerprint*)
  - Lokale Debug-Builds: `keytool -list -v -keystore mobile/android/app/debug.keystore -alias androiddebugkey -storepass android -keypass android`

## Schritte

1. **DNS:** A- bzw. AAAA-Eintrag `stadtfest.herderstreet.de` auf die öffentliche IP des Heimservers setzen (bei dynamischer IP über den vorhandenen DynDNS-Mechanismus).
2. **Fingerabdruck eintragen:** In `infra/deeplinks/public/.well-known/assetlinks.json` den Platzhalter durch den Fingerabdruck ersetzen (Format `AB:CD:…`). Mehrere Schlüssel (Debug und Release) sind als weitere Einträge der Liste möglich.
3. **Ausliefern:** Den Ordner `infra/deeplinks/public` als `/srv/deeplinks` bereitstellen und Caddy mit `infra/deeplinks/Caddyfile` starten. Caddy holt das TLS-Zertifikat automatisch.
   - `assetlinks.json` muss **ohne Weiterleitung** und mit `Content-Type: application/json` erreichbar sein.
   - Access-Logs sind abgeschaltet (keine IP-Adressen speichern).
4. **App bauen:** Der Intent-Filter entsteht in `mobile/app.config.ts` (`autoVerify: true`, Host aus `EXPO_PUBLIC_LINK_HOST`, Pfade `/f/`, `/freund/`, `/e/` und `/einladung/`). Für EAS-Builds die Variable als EAS-Umgebungsvariable setzen. Nach einer Änderung einen neuen Build erzeugen.
5. **iOS (später):** Mit Apple-Team-ID
   - `infra/deeplinks/public/.well-known/apple-app-site-association` anlegen (`applinks.details[].appIDs = ["<TEAMID>.de.stadtfestfinder.app"]`, `components: [{"/": "/f/*"}, {"/": "/freund/*"}, {"/": "/e/*"}, {"/": "/einladung/*"}]`), ohne Dateiendung, `Content-Type: application/json`
   - In `mobile/app.config.ts` `ios.associatedDomains: [`applinks:${LINK_HOST}`]` ergänzen und neu bauen.

## Prüfung

```bash
curl -sI https://stadtfest.herderstreet.de/.well-known/assetlinks.json
curl -s "https://digitalassetlinks.googleapis.com/v1/statements:list?source.web.site=https://stadtfest.herderstreet.de&relation=delegate_permission/common.handle_all_urls"
```

- Die erste Anfrage liefert `200` und `content-type: application/json`.
- Die zweite (Google Digital Asset Links API) listet `de.stadtfestfinder.app` mit dem Fingerabdruck.
- Auf dem Gerät bzw. Emulator: `adb shell pm get-app-links de.stadtfestfinder.app` zeigt `stadtfest.herderstreet.de: verified`.
- `adb shell am start -a android.intent.action.VIEW -d "https://stadtfest.herderstreet.de/f/<id>"` öffnet die Detailseite, auch bei geschlossener App.
- Genauso öffnen `…/e/<token>` die Einladungsvorschau und `…/einladung/<id>` die erhaltene Einladung (R14).
- Das App-Schema lässt sich ohne Domain prüfen: `xcrun simctl openurl booted "stadtfest://f/<id>"` bzw. `adb shell am start -d "stadtfest://f/<id>"`.

## Rollback

- Den Eintrag in `assetlinks.json` entfernen: Android öffnet die Links dann wieder im Browser (Fallback-Seite). Das App-Schema funktioniert weiter.
- Den Intent-Filter aus `mobile/app.config.ts` entfernen und neu bauen.
