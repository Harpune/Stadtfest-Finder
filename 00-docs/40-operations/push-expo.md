# Push über Expo einrichten

## Zweck

R11 verschickt Push-Mitteilungen (Erinnerungen, neue Feste am Wohnort, Änderungen, Absagen, Ende einer KI-Suche). Mit `PUSH_PROVIDER=expo` sendet das Backend an den Expo Push Service, der an Apple (APNs) und Google (FCM) weiterleitet ([ADR 0016](../25-adr/0016-benachrichtigungen-und-push.md)). Die App registriert dazu ein Expo-Push-Token.

## Voraussetzungen

- Konto auf [expo.dev](https://expo.dev) mit dem Projekt der App (EAS-Projekt, `extra.eas.projectId` in `mobile/app.json`)
- **Android:** Firebase-Projekt mit der Android-App `de.stadtfestfinder.app`; Expo braucht für FCM v1 den Dienstkonto-Schlüssel des Projekts
- **iOS:** Apple-Developer-Konto; EAS legt den APNs-Schlüssel beim ersten Build an oder übernimmt einen vorhandenen
- Ein Development- oder Release-Build der App (Expo Go genügt nicht); nach dem Hinzufügen von `expo-notifications` und `google-services.json` muss der native Build neu erstellt werden (`cd mobile && npx expo run:android` oder `npx eas-cli build --profile development --platform android`)

## Schritte

1. **EAS-Projekt verknüpfen:** `cd mobile && npx eas-cli login` (Expo-Konto), dann `npx eas-cli init`. Die Projekt-ID landet in `app.json` unter `extra.eas.projectId`; die App braucht sie für `getExpoPushTokenAsync`. Die Build-Profile stehen in `mobile/eas.json` (`development`, `preview`, `production`); ohne diese Datei bricht `eas credentials` mit „eas.json could not be found“ ab.
2. **Android (FCM v1):**
   1. In der [Firebase-Konsole](https://console.firebase.google.com) ein Projekt anlegen und die Android-App mit dem Paketnamen `de.stadtfestfinder.app` hinzufügen.
   2. `google-services.json` herunterladen und nach `mobile/google-services.json` legen. Die Datei enthält nur öffentliche Projektkennungen und darf ins Repo. In `mobile/app.json` unter `android` den Eintrag `"googleServicesFile": "./google-services.json"` ergänzen, damit der native Build Firebase kennt (sonst bekommt die App auf Android kein Push-Token).
   3. Firebase-Konsole → Zahnrad → Projekteinstellungen → Tab **Dienstkonten** → „Neuen privaten Schlüssel generieren“. Es wird eine JSON-Datei heruntergeladen (`<projekt>-firebase-adminsdk-….json`). Sie enthält einen privaten Schlüssel: **nicht** ins Repo legen (die Muster stehen in `mobile/.gitignore`), am besten außerhalb des Repos ablegen.
   4. Den Schlüssel bei Expo hinterlegen, wahlweise:
      - **Im Browser (einfachster Weg):** [expo.dev](https://expo.dev) → Projekt `stadtfest-finder` → **Credentials** → Android → Application Identifier `de.stadtfestfinder.app` auswählen bzw. mit „Add Application Identifier“ anlegen → **Service Credentials** → „FCM V1 service account key“ → **Add a service account key** → „Upload new key“ → JSON-Datei wählen → **Save**.
      - **Per CLI:** `cd mobile && npx eas-cli credentials` → `Android` → Build-Profil `development` (der Schlüssel gilt für die App-ID, also für alle Profile) → `Google Service Account` → `Manage your Google Service Account Key for Push Notifications (FCM V1)` → `Set up a Google Service Account Key for Push Notifications (FCM V1)` → `Upload a new service account key` → Pfad zur JSON-Datei angeben.
   5. Danach die JSON-Datei lokal löschen oder sicher verwahren; Expo braucht sie nicht erneut.
3. **iOS (APNs):** `npx eas-cli credentials` → iOS → „Push Notifications: Manage your Apple Push Notifications Key“ → neuen Schlüssel erzeugen lassen.
4. **Zugriffstoken:** expo.dev → Account settings → Access tokens → „Create token“ (Name z. B. `stadtfest-backend`). Unter Projekteinstellungen → „Push notifications“ die Option **Enhanced security for push notifications** einschalten, damit nur das Backend mit diesem Token senden darf.
5. Secrets hinterlegen: lokal in `.env` `PUSH_PROVIDER=expo` und `EXPO_ACCESS_TOKEN=…` (siehe `.env.example`), in Produktion als Komodo-Secret. **Niemals ins Repo.**
6. API und Worker neu starten. Ohne `EXPO_ACCESS_TOKEN` bricht der Start mit einer Fehlermeldung ab.

## Prüfung

1. `curl -s localhost:8000/v1/config` liefert `{"pushProvider":"expo"}`.
2. In der App anmelden, ein Fest als Favorit merken und die Mitteilungen erlauben. In der Tabelle `device` steht danach ein Token `ExponentPushToken[…]` mit `provider = expo`.
3. Als Moderator das Fest absagen. Nach wenigen Sekunden kommt der Push „Fest abgesagt“, die Benachrichtigungsliste zeigt den Eintrag, der Zähler am Profilbild steigt.
4. Optional ohne App: [Expo Push Notifications Tool](https://expo.dev/notifications) mit dem Token aus `device`.

## Rollback

`PUSH_PROVIDER=disabled` (oder `direct`, siehe [push-apns-fcm.md](push-apns-fcm.md)) setzen und API und Worker neu starten. Die Liste in der App funktioniert weiter, es gehen keine Daten mehr an Expo. Das Zugriffstoken auf expo.dev widerrufen, wenn es nicht mehr gebraucht wird.
