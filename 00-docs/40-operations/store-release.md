# Store-Release (App Store, Google Play)

## Zweck

Die Production-Builds aus [eas-build.md](eas-build.md) kommen zuerst als TestFlight- bzw. interne Testversion zu den Testern, danach in die Stores (R16-US6). Diese Anleitung sammelt die Store-Anforderungen: Datenschutzangaben, Kontolöschung, Sign in with Apple, Berechtigungstexte, Impressum und Datenschutzerklärung.

## Voraussetzungen

- **Apple Developer Program** (99 €/Jahr), Rolle Admin in App Store Connect
- **Google Play Console** (einmalig 25 $), Entwicklerkonto verifiziert
- Production-Stack läuft, `https://stadtfest.herderstreet.de/datenschutz/` und `/impressum/` sind erreichbar ([deployment-komodo.md](deployment-komodo.md))
- Rechtliche Prüfung von Datenschutzerklärung, Impressum und Nutzungsbedingungen (`infra/deeplinks/public/…`, Entwurf aus R16, aus dem [VVT](../30-privacy/verarbeitungsverzeichnis.md) abgeleitet)

## Schritte

### 1. Apps anlegen

1. **App Store Connect:** *Apps → +*, Bundle-ID `de.stadtfestfinder.app`, Name „Stadtfest-Finder“, Primärsprache Deutsch. Die App-ID (`ascAppId`) notieren.
2. **Play Console:** *App erstellen*, Paketname `de.stadtfestfinder.app`, Standardsprache Deutsch, kostenlos. Unter *App-Integrität → App-Signatur* „Play App Signing“ nutzen und den SHA-256 des **App-Signaturschlüssels** zusätzlich in `ANDROID_CERT_SHA256` eintragen ([deep-links-domain.md](deep-links-domain.md)).
3. **Erste Android-Version** einmal von Hand hochladen (Google verlangt das vor der API-Einreichung): AAB aus EAS herunterladen, *Testen → Interner Test → Neuer Release*. Danach ein Dienstkonto für EAS Submit anlegen (*Einrichtung → API-Zugriff*) und mit `npx eas-cli@latest credentials -p android` hinterlegen.
4. **iOS-Einreichung:** `npx eas-cli@latest submit -p ios --profile production` fragt beim ersten Mal den App-Store-Connect-API-Schlüssel ab und speichert ihn bei EAS.

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
- Auftragsverarbeiter (Zitadel, Apple/Google für Push, Hetzner) gelten nicht als „Teilen“.
- **Web-Link zur Kontolöschung** (Pflicht bei Play): `https://stadtfest.herderstreet.de/datenschutz/` (Abschnitt „Konto löschen“, Kontakt per E-Mail für Löschanfragen ohne App).

### 3. Weitere Store-Anforderungen

| Anforderung | Umsetzung |
|---|---|
| Kontolöschung in der App | Konto → „Konto löschen“ (R05, Löschkonzept); in den Review-Hinweisen nennen |
| Sign in with Apple | Zitadel-IdP Apple, Button „Mit Apple fortfahren“ (R05, [zitadel.md](zitadel.md)) |
| Berechtigungstexte (Deutsch) | Standort und Fotos in `mobile/app.json` (`expo-location`, `expo-image-picker`); Mitteilungen nutzen den Systemtext von iOS/Android |
| Impressum, Datenschutz | Links im Drawer-Fußbereich (Gast und angemeldet); der Einstieg-Screen verlinkt Datenschutzerklärung und Nutzungsbedingungen |
| Export-Compliance | `ios.config.usesNonExemptEncryption: false` (nur HTTPS) |
| Demo-Zugang für die Prüfung | eigenes Testkonto in Zitadel (Rolle `user`, optional `moderator`), Zugangsdaten nur in App Store Connect / Play Console eintragen |
| Altersfreigabe | Fragebogen: keine bedenklichen Inhalte; nutzergenerierte Inhalte nur unter Freunden (Einladungen, Listen) |

### 4. Testversionen verteilen

1. Tag setzen: `git tag v1.0.0 && git push origin v1.0.0` → Workflow „EAS build“ baut und reicht ein.
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
