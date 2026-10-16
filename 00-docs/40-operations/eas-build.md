# App-Builds mit EAS

## Zweck

iOS- und Android-Builds entstehen mit EAS Build, getrennt von den Docker-Images (R16-US6). Der Workflow `.github/workflows/eas-build.yml` startet sie:

| Auslöser | Profil | Ergebnis |
|---|---|---|
| *Actions → EAS build → Run workflow*, Profil `preview` | `preview` | interne Verteilung: Android-APK, iOS Ad-hoc (registrierte Geräte) |
| *Run workflow*, Profil `production`, optional „submit“ | `production` | Store-Builds (AAB, IPA), mit „submit“ an TestFlight bzw. Play-Testtrack „Intern“ |
| Git-Tag `v1.2.3` | `production` | Store-Builds für beide Plattformen, automatisch eingereicht |

Profile und Submit-Ziele stehen in `mobile/eas.json`; die Versionsnummer zählt EAS hoch (`appVersionSource: remote`, `autoIncrement`).

## Voraussetzungen

- Expo-Konto mit Zugriff auf das Projekt `@harpune/stadtfest-finder` (Projekt-ID in `mobile/app.json`)
- Apple Developer Program (Rolle Admin) und Google-Play-Developer-Konto ([store-release.md](store-release.md))
- Zitadel-Produktion eingerichtet ([zitadel.md](zitadel.md)), Domain für Deep Links ([deep-links-domain.md](deep-links-domain.md))

## Schritte

1. **Access-Token:** expo.dev → *Account settings → Access tokens → Create* (Name `github-actions`). Als GitHub-Secret `EXPO_TOKEN` hinterlegen. **Niemals ins Repo.**
2. **EAS-Umgebungsvariablen** je Umgebung (`preview`, `production`) auf expo.dev → Projekt → *Environment variables* bzw. per CLI, z. B.:
   ```bash
   cd mobile
   npx eas-cli@latest env:create --environment production --name EXPO_PUBLIC_API_URL --value https://api.stadtfest.herderstreet.de --visibility plaintext
   ```
   | Variable | Produktion |
   |---|---|
   | `EXPO_PUBLIC_API_URL` | `https://api.stadtfest.herderstreet.de` |
   | `EXPO_PUBLIC_LINK_HOST` | `stadtfest.herderstreet.de` |
   | `EXPO_PUBLIC_AUTH_*` | aus [zitadel.md](zitadel.md), Schritt 6 |
   | `EXPO_PUBLIC_MAPTILER_KEY` | Schlüssel aus [maptiler.md](maptiler.md) (Sichtbarkeit „sensitive“) |

   `EXPO_PUBLIC_*`-Werte landen im App-Bundle und sind damit **nicht geheim**; echte Secrets gehören nicht in die App.
3. **Signierschlüssel und Push-Credentials** (einmalig, interaktiv auf dem Rechner):
   ```bash
   cd mobile
   npx eas-cli@latest credentials -p ios      # Distribution Certificate, Provisioning Profile, Push Key
   npx eas-cli@latest credentials -p android  # Keystore erzeugen lassen
   ```
   - iOS: EAS legt App-ID-Capabilities an (Push Notifications, Associated Domains). Für `PUSH_PROVIDER=direct` den APNs-Schlüssel aus [push-apns-fcm.md](push-apns-fcm.md) verwenden.
   - Android: Den **SHA-256-Fingerabdruck** des Keystores (und später des Play-App-Signing-Schlüssels aus der Play Console) in die Stack-Umgebung `ANDROID_CERT_SHA256` eintragen (kommagetrennt) und deployen, sonst werden App Links nicht verifiziert.
   - Die Apple-Team-ID als `APPLE_TEAM_ID` in die Stack-Umgebung (Universal Links).
4. **Preview-Build** starten (Workflow, Profil `preview`) und auf einem Testgerät installieren (Link aus der EAS-Build-Seite).
5. **Production-Build** mit „submit“ bzw. per Tag; Einreichung siehe [store-release.md](store-release.md).

## Prüfung

- Der Workflow-Lauf endet grün und verlinkt die Builds (`--no-wait`: der Build läuft auf EAS weiter; Status auf expo.dev).
- Preview-App: Anmeldung über Zitadel, Kartenkacheln laden, `https://stadtfest.herderstreet.de/f/<id>` öffnet die App (Android: `adb shell pm get-app-links de.stadtfestfinder.app` zeigt `verified`).
- `npx expo config --type prebuild` zeigt `ios.associatedDomains` und `ios.config.usesNonExemptEncryption: false`.

## Rollback

- Fehlerhafter Build: in TestFlight bzw. der Play Console nicht freigeben oder den vorherigen Build erneut zur Prüfung geben.
- Kompromittiertes `EXPO_TOKEN`: auf expo.dev widerrufen, neues Token als GitHub-Secret setzen.
- Falsche `EXPO_PUBLIC_*`-Werte wirken erst mit einem neuen Build; korrigieren und neu bauen.
