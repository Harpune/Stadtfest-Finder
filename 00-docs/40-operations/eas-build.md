# App-Builds mit EAS

## Zweck

iOS- und Android-Builds entstehen mit EAS Build, getrennt von den Docker-Images (R16-US6). Der Workflow `.github/workflows/eas-build.yml` startet sie:

| Auslöser | Profil | Ergebnis |
|---|---|---|
| *Actions → EAS build → Run workflow*, Profil `preview` | `preview` | interne Verteilung: Android-APK, iOS Ad-hoc (registrierte Geräte) |
| *Run workflow*, Profil `production`, optional „submit“ | `production` | Store-Builds (AAB, IPA), mit „submit“ an TestFlight bzw. Play-Testtrack „Intern“ |
| Git-Tag `v1.2.3` | `production` | Store-Build für Android (AAB), automatisch an den Play-Testtrack „Intern“ eingereicht |

**iOS ist vorerst ausgesetzt**, solange es kein Apple-Developer-Konto gibt: Tags bauen nur Android, und *Run workflow* steht standardmäßig auf `android`. Ein iOS-Build geht weiterhin von Hand (Plattform `ios` oder `all`), sobald die iOS-Zugangsdaten bei EAS eingerichtet sind (Schritt 3).

Profile und Submit-Ziele stehen in `mobile/eas.json`; die Build-Nummer zählt EAS hoch (`appVersionSource: remote`, `autoIncrement`). Derselbe Tag baut auch die Backend-Images ([deployment-komodo.md](deployment-komodo.md)).

## Voraussetzungen

- Expo-Konto mit Zugriff auf das Projekt `@harpune/stadtfest-finder` (Projekt-ID in `mobile/app.json`)
- Apple Developer Program und Google-Play-Developer-Konto ([store-release.md](store-release.md), Schritt 1)
- Erledigt: [Zitadel](zitadel.md) (App-Werte), [MapTiler](maptiler.md) (Schlüssel)

### Werte, die in dieser Anleitung entstehen bzw. gebraucht werden

| Wert | Quelle | wird eingetragen in |
|---|---|---|
| Expo-Access-Token | Schritt 1 | GitHub-Repository-Secret `EXPO_TOKEN` |
| `EXPO_PUBLIC_*`-Werte | Schritt 2 (Tabelle) | EAS-Umgebungen `production` und `preview` |
| SHA-256 des Android-Keystores | Schritt 3 | Komodo-Variable `STADTFEST_ANDROID_CERT_SHA256` |
| Apple-Team-ID | [push-apns-fcm.md](push-apns-fcm.md), Schritt 1 | Komodo-Variable `STADTFEST_APPLE_TEAM_ID` (schon gesetzt) |

## Schritte

1. **Access-Token:** expo.dev → *Account settings → Access tokens → Create token* (Name `github-actions`). GitHub → Repo `Harpune/Stadtfest-Finder` → *Settings → Secrets and variables → Actions → New repository secret* `EXPO_TOKEN`. **Niemals ins Repo.**
2. **EAS-Umgebungsvariablen:** expo.dev → Projekt → *Environment variables* → **Add variable**, jeweils für die Umgebungen **production** und **preview** (Preview-Builds sprechen dasselbe Backend an, solange es kein Staging gibt). Per CLI geht es so:
   ```bash
   cd mobile
   npx eas-cli@latest env:create --environment production --environment preview \
     --name EXPO_PUBLIC_API_URL --value https://stadtfest-api.herderstreet.de --visibility plaintext
   ```
   | Variable | Wert | Sichtbarkeit | Quelle |
   |---|---|---|---|
   | `EXPO_PUBLIC_API_URL` | `https://stadtfest-api.herderstreet.de` | Plain text | [deployment-komodo.md](deployment-komodo.md) |
   | `EXPO_PUBLIC_LINK_HOST` | `stadtfest.herderstreet.de` | Plain text | [deep-links-domain.md](deep-links-domain.md) |
   | `EXPO_PUBLIC_AUTH_ISSUER` | Zitadel-Instanz-URL | Plain text | [zitadel.md](zitadel.md), Schritt 0 |
   | `EXPO_PUBLIC_AUTH_CLIENT_ID` | Client-ID der Native-App | Plain text | [zitadel.md](zitadel.md), Schritt 2 |
   | `EXPO_PUBLIC_AUTH_IDP` | `zitadel` | Plain text | – |
   | `EXPO_PUBLIC_AUTH_PROJECT_ID` | Projekt-ID | Plain text | [zitadel.md](zitadel.md), Schritt 1 |
   | `EXPO_PUBLIC_AUTH_APPLE_IDP` | IdP-ID Apple | Plain text | [zitadel.md](zitadel.md), Schritt 3 |
   | `EXPO_PUBLIC_AUTH_GOOGLE_IDP` | IdP-ID Google | Plain text | [zitadel.md](zitadel.md), Schritt 3 |
   | `EXPO_PUBLIC_MAPTILER_KEY` | MapTiler-Schlüssel `stadtfest-app-prod` | Sensitive | [maptiler.md](maptiler.md), Schritt 2 |
   | `EXPO_PUBLIC_MAPTILER_STYLE_DARK` / `_LIGHT` | optional, Standard `streets-v2-dark` / `streets-v2` | Plain text | [maptiler.md](maptiler.md) |

   `EXPO_PUBLIC_*`-Werte landen im App-Bundle und sind damit **nicht geheim**; echte Secrets gehören nie in die App.
3. **Signierschlüssel und Capabilities** (einmalig, interaktiv auf dem Rechner):
   ```bash
   cd mobile
   npx eas-cli@latest login
   npx eas-cli@latest credentials -p ios      # Apple-Login; Distribution Certificate + Provisioning Profile erzeugen lassen
   npx eas-cli@latest credentials -p android  # Keystore erzeugen lassen
   ```
   - iOS: EAS legt die App-ID mit den Capabilities Push Notifications, Associated Domains und Sign in with Apple an. Ein APNs-Schlüssel **bei EAS** ist für `PUSH_PROVIDER=direct` nicht nötig (die Frage danach mit „No“ beantworten); den Schlüssel bekommt das Backend ([push-apns-fcm.md](push-apns-fcm.md)).
   - Android: `credentials -p android` → *Keystore* zeigt den **SHA256 Fingerprint** (`AB:CD:…`) → Komodo-Variable `STADTFEST_ANDROID_CERT_SHA256` setzen und den Stack `stadtfest` neu deployen. Nach dem ersten Play-Upload kommt der Fingerabdruck des **App-Signaturschlüssels** aus der Play Console dazu, kommagetrennt ([store-release.md](store-release.md), Schritt 1).
4. **Preview-Build** starten (Workflow, Profil `preview`) und auf einem Testgerät installieren (Link auf der Build-Seite von expo.dev). iOS-Testgeräte vorher registrieren: `npx eas-cli@latest device:create`.
5. **Production-Build** mit „submit“ bzw. per Tag; Einreichung siehe [store-release.md](store-release.md).

## Prüfung

- Der Workflow-Lauf endet grün und verlinkt die Builds (`--no-wait`: der Build läuft auf EAS weiter; Status auf expo.dev).
- Preview-App: Anmeldung über Zitadel, Kartenkacheln laden, `https://stadtfest.herderstreet.de/f/<id>` öffnet die App (Android: `adb shell pm get-app-links de.stadtfestfinder.app` zeigt `verified`).
- `npx expo config --type prebuild` zeigt `ios.associatedDomains` und `ios.config.usesNonExemptEncryption: false`.

## Rollback

- Fehlerhafter Build: in TestFlight bzw. der Play Console nicht freigeben oder den vorherigen Build erneut zur Prüfung geben.
- Kompromittiertes `EXPO_TOKEN`: auf expo.dev widerrufen, neues Token als GitHub-Secret setzen.
- Falsche `EXPO_PUBLIC_*`-Werte wirken erst mit einem neuen Build; korrigieren und neu bauen.
