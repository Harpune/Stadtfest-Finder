# Store-Release (App Store, Google Play)

## Zweck

Die Production-Builds aus [eas-build.md](eas-build.md) kommen zuerst als TestFlight- bzw. interne Testversion zu den Testern, danach in die Stores (R16-US6). Diese Anleitung sammelt die Store-Anforderungen: Datenschutzangaben, Kontolöschung, Sign in with Apple, Berechtigungstexte, Impressum und Datenschutzerklärung.

## Voraussetzungen

- **Apple Developer Program** (99 €/Jahr), Rolle Admin in App Store Connect
- **Google Play Console** (einmalig 25 $), Entwicklerkonto verifiziert
- Production-Stack läuft, `https://stadtfest.herderstreet.de/datenschutz/` und `/impressum/` sind erreichbar ([deployment-komodo.md](deployment-komodo.md))
- Rechtliche Prüfung von Datenschutzerklärung, Impressum und Nutzungsbedingungen (`infra/edge/public/…`, Entwurf aus R16, aus dem [VVT](../30-privacy/verarbeitungsverzeichnis.md) abgeleitet)

### Werte, die in dieser Anleitung entstehen

| Wert | entsteht in | wird eingetragen in |
|---|---|---|
| App-Store-Connect-App-ID (`ascAppId`, nur Ziffern) | Abschnitt 1, Punkt 1 | `mobile/eas.json` → `submit.production.ios.ascAppId` (PR; nicht geheim) |
| App-Store-Connect-API-Schlüssel (`.p8`, Key ID, Issuer ID) | Abschnitt 1, Punkt 4 | bei EAS gespeichert (`eas credentials`), nirgends sonst |
| Google-Play-Dienstkonto (JSON) | Abschnitt 1, Punkt 3 | bei EAS gespeichert (`eas credentials`), danach lokal löschen |
| SHA-256 des Play-App-Signaturschlüssels | Abschnitt 1, Punkt 2 | Komodo-Variable `STADTFEST_ANDROID_CERT_SHA256` (zusätzlich zum EAS-Keystore, kommagetrennt) |
| Demo-Konto für die Prüfung | Abschnitt „Weitere Store-Anforderungen“ | nur in App Store Connect / Play Console |

## Schritte

### 1. Apps anlegen

1. **App Store Connect:** *Apps → + → Neue App*, Plattform iOS, Name „Stadtfest-Finder“, Primärsprache Deutsch, Bundle-ID `de.stadtfestfinder.app`, SKU `stadtfest-finder`. Die **Apple ID** der App (*App-Informationen → Allgemein*, nur Ziffern) ist die `ascAppId` → in `mobile/eas.json` unter `submit.production.ios` als `"ascAppId": "<ziffern>"` eintragen (PR). Ohne sie bricht `--auto-submit` im Workflow für iOS ab, weil er nicht nachfragen kann.
2. **Play Console:** *App erstellen*, Paketname `de.stadtfestfinder.app`, Standardsprache Deutsch, kostenlos. Unter *App-Integrität → App-Signatur* „Play App Signing“ nutzen; den SHA-256 des **App-Signaturschlüssels** (dort angezeigt) zusätzlich, kommagetrennt, in die Komodo-Variable `STADTFEST_ANDROID_CERT_SHA256` eintragen und den Stack neu deployen ([deep-links-domain.md](deep-links-domain.md)).
3. **Erste Android-Version** einmal von Hand hochladen (Google verlangt das vor der API-Einreichung): AAB aus EAS herunterladen, *Testen → Interner Test → Neuer Release*. Danach das Dienstkonto für EAS Submit:
   1. [Google Cloud Console](https://console.cloud.google.com) (Projekt `stadtfest`) → *IAM & Admin → Service Accounts → Create*, Name `eas-submit`, ohne Projektrolle → *Keys → Add key → JSON* herunterladen.
   2. Play Console → *Nutzer und Berechtigungen → Neue Nutzer einladen* → E-Mail des Dienstkontos, App `Stadtfest-Finder`, Berechtigung „Releases verwalten“ (Testtracks).
   3. `cd mobile && npx eas-cli@latest credentials -p android` → *Google Service Account* → *Upload a Google Service Account Key* → JSON-Datei. Danach die Datei lokal löschen.
4. **iOS-Einreichung:** App Store Connect → *Benutzer und Zugriff → Integrationen → App Store Connect API → +*, Name `eas-submit`, Rolle „App Manager“ → `.p8` herunterladen (einmalig), Key ID und Issuer ID notieren. Dann `cd mobile && npx eas-cli@latest credentials -p ios` → *App Store Connect: Manage your API Key* → Schlüssel hochladen. Danach kann der Workflow ohne Rückfrage einreichen.

### 2. Datenschutzangaben

Abgeleitet aus dem VVT; **kein Tracking, keine Werbung, keine Analyse**, alle Übertragungen per HTTPS.

**App Store – App-Datenschutz („Privacy Nutrition Label“)**

| Datentyp (Apple) | Zweck | Mit Identität verknüpft | Quelle |
|---|---|---|---|
| Kontaktinformationen: Name | App-Funktionalität | ja | Konto (VVT 5) |
| Kontaktinformationen: E-Mail-Adresse | App-Funktionalität | ja | Anmeldung bei Zitadel (VVT 6) |
| Standort: Ungefährer Standort | App-Funktionalität | nein (gerundet, nicht gespeichert); Wohnort-PLZ: ja | VVT 2, 12 |
| Benutzerinhalte: Fotos | App-Funktionalität | ja (nur Moderierende) | VVT 9 |
| Benutzerinhalte: Andere | App-Funktionalität | ja (Listennamen, Einladungstexte) | VVT 15, 16 |
| IDs: Benutzer-ID | App-Funktionalität | ja | VVT 5 |

„Daten zum Tracking verwendet“: **nein**. Nicht erhoben: Finanzdaten, Gesundheit, Kontakte, Browserverlauf, Suchverlauf (Suchtexte werden nicht gespeichert), Diagnose, Nutzungsdaten.

**Google Play – Datensicherheit („Data Safety“)**

| Kategorie | Erhoben | Geteilt | Zweck | Optional |
|---|---|---|---|---|
| Personenbezogene Daten: Name, E-Mail, Nutzer-IDs | ja | nein | App-Funktionen, Kontoverwaltung | nein (nur mit Konto) |
| Standort: Ungefährer Standort | ja | nein | App-Funktionen | ja |
| Fotos | ja | nein | App-Funktionen | ja (nur Moderierende) |
| Nachrichten / sonstige Inhalte (Einladungstexte, Listennamen) | ja | nein | App-Funktionen | ja |
| Geräte- oder andere IDs (Push-Token) | ja | nein | App-Funktionen (Mitteilungen) | ja |

- „Daten werden bei der Übertragung verschlüsselt“: **ja**. „Nutzer können das Löschen ihrer Daten anfordern“: **ja**.
- Auftragsverarbeiter (Zitadel, Cloudflare, Apple/Google für Push, pCloud für Backups) gelten nicht als „Teilen“.
- **Web-Link zur Kontolöschung** (Pflicht bei Play): `https://stadtfest.herderstreet.de/datenschutz/` (Abschnitt „Konto löschen“, Kontakt per E-Mail für Löschanfragen ohne App).

### 3. Weitere Store-Anforderungen

| Anforderung | Umsetzung |
|---|---|
| Kontolöschung in der App | Konto → „Konto löschen“ (R05, Löschkonzept); in den Review-Hinweisen nennen |
| Sign in with Apple | Zitadel-IdP Apple, Button „Mit Apple fortfahren“ (R05, [zitadel.md](zitadel.md)) |
| Berechtigungstexte (Deutsch) | Standort und Fotos in `mobile/app.json` (`expo-location`, `expo-image-picker`); Mitteilungen nutzen den Systemtext von iOS/Android |
| Impressum, Datenschutz | Links im Drawer-Fußbereich (Gast und angemeldet); der Einstieg-Screen verlinkt Datenschutzerklärung und Nutzungsbedingungen |
| Export-Compliance | `ios.config.usesNonExemptEncryption: false` (nur HTTPS) |
| Demo-Zugang für die Prüfung | eigenes Testkonto in Zitadel (E-Mail-Anmeldung, Rolle `user` über die Action, optional `moderator`), Zugangsdaten nur in App Store Connect (*App-Review-Informationen*) bzw. Play Console (*App-Inhalte → App-Zugriff*) eintragen |
| Altersfreigabe | Fragebogen: keine bedenklichen Inhalte; nutzergenerierte Inhalte nur unter Freunden (Einladungen, Listen) |

### 4. Testversionen verteilen

1. *Actions → EAS build → Run workflow* mit Profil `production` und „submit“ → baut und reicht ein. (Ein Tag baut nur die APK, [eas-build.md](eas-build.md).)
2. **TestFlight:** Build erscheint nach der Verarbeitung; interne Tester (App-Store-Connect-Nutzer) bekommen ihn sofort, externe nach der Beta-Prüfung.
3. **Play:** *Testen → Interner Test* → Tester-Liste (E-Mail-Adressen) → Link teilen.

### 5. Veröffentlichung

Nach erfolgreichem Test: App Store *Zur Prüfung einreichen*; Play: Release vom internen Test in *Produktion* hochstufen (stufenweise Einführung, z. B. 20 %).

## Prüfung

- TestFlight und Play-Interntest zeigen die Version mit Build-Nummer aus EAS.
- Auf einem Testgerät: Anmeldung (Apple, Google, E-Mail), Kontolöschung, Mitteilung empfangen, Deep Link `https://stadtfest.herderstreet.de/f/<id>` öffnet die App.
- Datenschutzangaben stimmen mit dem VVT überein (bei jeder Änderung des VVT prüfen).

## Rollback

- App Store: fehlerhafte Version nicht freigeben bzw. *Aus dem Verkauf nehmen*; einen korrigierten Build einreichen (kein Downgrade möglich).
- Play: stufenweise Einführung anhalten, korrigierten Release mit höherer Versionsnummer nachschieben.
- Backend-Änderungen bleiben abwärtskompatibel zur Vorversion der App (API-Versionierung, oasdiff im CI).
