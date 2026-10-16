# Deep Links und Domain einrichten

## Zweck

Links wie `https://stadtfest.herderstreet.de/f/{eventId}` öffnen die Detailseite in der App (R04-US6), Freundschaftslinks `https://stadtfest.herderstreet.de/freund/{token}` das Annehmen der Freundschaft (R12), Einladungslinks `…/e/{token}` die Einladungsvorschau und `…/einladung/{invitationId}` eine erhaltene Einladung (R14). Ohne installierte App zeigt die Domain eine einfache Seite. Zusätzlich funktioniert immer das App-Schema `stadtfest://f/{eventId}`, `stadtfest://freund/{token}`, `stadtfest://e/{token}` bzw. `stadtfest://einladung/{invitationId}`.

**Domain konfigurierbar:** `EXPO_PUBLIC_LINK_HOST` (Standard `stadtfest.herderstreet.de`) bestimmt den Host der geteilten Links und des Android-Intent-Filters (`mobile/app.config.ts`). Für App Links wirkt eine Änderung erst mit einem neuen Build. Das Image `stadtfest-edge` liest denselben Host aus `LINK_HOST` (im HomeLab `stadtfest.${DOMAIN}`).

**Stand (R16):** Android App Links und iOS Universal Links sind konfiguriert. `stadtfest-edge` rendert `assetlinks.json` und `apple-app-site-association` aus den Komodo-Variablen `STADTFEST_ANDROID_CERT_SHA256` und `STADTFEST_APPLE_TEAM_ID`; solange sie leer sind, liefern beide Dateien eine leere Liste.

**Werte, die hier gebraucht werden:** SHA-256-Fingerabdrücke der Android-Signaturschlüssel ([eas-build.md](eas-build.md), Schritt 3; [store-release.md](store-release.md), Abschnitt 1, Punkt 2) → Komodo-Variable `STADTFEST_ANDROID_CERT_SHA256` (kommagetrennt); Apple-Team-ID → `STADTFEST_APPLE_TEAM_ID`; Impressumsangaben → `STADTFEST_IMPRINT_NAME`, `STADTFEST_IMPRINT_ADDRESS`, `STADTFEST_IMPRINT_EMAIL`; Link-Host → EAS-Variable `EXPO_PUBLIC_LINK_HOST`.

## Voraussetzungen

- Cloudflare-Zugang (Tunnel-Hostnamen, [deployment-komodo.md](deployment-komodo.md), Schritt 2)
- Der HomeLab-Stack `stadtfest` ([deployment-komodo.md](deployment-komodo.md)); Routing und Dateien stecken im Image `stadtfest-edge` (`infra/edge/Caddyfile`, `infra/edge/public/`)
- Der SHA-256-Fingerabdruck des Android-Signaturschlüssels:
  - Release: aus EAS (`npx eas-cli@latest credentials -p android` → *Keystore* → *SHA256 Fingerprint*)
  - Lokale Debug-Builds: `keytool -list -v -keystore mobile/android/app/debug.keystore -alias androiddebugkey -storepass android -keypass android`

## Schritte

1. **Erreichbarkeit:** Tunnel-Hostname `stadtfest.herderstreet.de` → `https://caddy:443` ([deployment-komodo.md](deployment-komodo.md), Schritt 2); den DNS-Eintrag legt Cloudflare an.
2. **Fingerabdrücke eintragen:** Komodo-Variable `STADTFEST_ANDROID_CERT_SHA256` setzen (Format `AB:CD:…`, mehrere Schlüssel kommagetrennt: EAS-Keystore und Play-App-Signing-Schlüssel). Für iOS `STADTFEST_APPLE_TEAM_ID` (Apple-Developer-Konto → *Membership*). Danach den Stack `stadtfest` deployen.
3. **Ausliefern:** `stadtfest-edge` liefert `infra/edge/public` unter `LINK_HOST` aus; TLS übernimmt der HomeLab-Caddy.
   - `/.well-known/assetlinks.json` und `/.well-known/apple-app-site-association` kommen **ohne Weiterleitung** mit `Content-Type: application/json` (Templates in `infra/edge/public/.well-known/`).
   - Access-Logs sind abgeschaltet (keine IP-Adressen speichern).
   - Unter `/impressum/`, `/datenschutz/` und `/nutzungsbedingungen/` liegen die Rechtstexte; die Impressumsangaben kommen aus `IMPRINT_NAME`, `IMPRINT_ADDRESS`, `IMPRINT_EMAIL`.
4. **App bauen:** Der Intent-Filter (Android, `autoVerify: true`, Pfade `/f/`, `/freund/`, `/e/`, `/einladung/`) und `ios.associatedDomains` (`applinks:<LINK_HOST>`) entstehen in `mobile/app.config.ts` aus `EXPO_PUBLIC_LINK_HOST`. Für EAS-Builds die Variable in der EAS-Umgebung setzen ([eas-build.md](eas-build.md)); nach einer Änderung neu bauen.

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

- `STADTFEST_ANDROID_CERT_SHA256` bzw. `STADTFEST_APPLE_TEAM_ID` leeren und deployen: Die Links öffnen dann wieder im Browser (Fallback-Seite). Das App-Schema funktioniert weiter.
- Den Intent-Filter aus `mobile/app.config.ts` entfernen und neu bauen.
