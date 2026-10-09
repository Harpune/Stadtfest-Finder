# Push direkt über APNs und FCM einrichten

## Zweck

Mit `PUSH_PROVIDER=direct` sendet das Backend selbst an Apple (APNs, iOS) und Google (FCM HTTP v1, Android). Expo fällt als zusätzlicher Verarbeiter weg ([ADR 0016](../25-adr/0016-benachrichtigungen-und-push.md)). Die App registriert dann das native Geräte-Token (`getDevicePushTokenAsync`).

## Voraussetzungen

- Apple-Developer-Konto (Rolle Admin) für die App-ID `de.stadtfestfinder.app` mit der Capability „Push Notifications“
- Firebase-Projekt mit der Android-App `de.stadtfestfinder.app` (siehe [push-expo.md](push-expo.md), Schritt 2.1–2.2)
- Ein Build der App, der die Push-Berechtigung enthält (`expo-notifications`-Plugin)

## Schritte

1. **APNs-Schlüssel:** [developer.apple.com](https://developer.apple.com/account/resources/authkeys/list) → Keys → „+“ → „Apple Push Notifications service (APNs)“ aktivieren → Schlüssel herunterladen (`AuthKey_<KEYID>.p8`, nur einmal möglich). Key-ID und Team-ID notieren.
2. **FCM-Dienstkonto:** Firebase-Konsole → Projekteinstellungen → Dienstkonten → „Neuen privaten Schlüssel generieren“ → JSON-Datei speichern. Die Projekt-ID steht unter „Allgemein“.
3. Secrets hinterlegen: lokal in `.env`, in Produktion als Komodo-Secret bzw. gemountete Dateien unter `/run/secrets/`. **Niemals ins Repo.**
   ```bash
   PUSH_PROVIDER=direct
   APNS_KEY_ID=<KEYID>
   APNS_TEAM_ID=<TEAMID>
   APNS_KEY_PATH=/run/secrets/apns.p8
   APNS_TOPIC=de.stadtfestfinder.app
   APNS_SANDBOX=false          # true für Development-Builds aus Xcode/EAS (development)
   FCM_PROJECT_ID=<projekt-id>
   FCM_CREDENTIALS_PATH=/run/secrets/fcm.json
   ```
4. API und Worker neu starten. Fehlt ein Wert oder ist eine Datei nicht lesbar, bricht der Start mit dem Namen der Variable ab.
5. Die App meldet sich nach dem nächsten Start bzw. Login mit dem nativen Token neu an (`GET /v1/config` liefert `direct`). Expo-Tokens aus der Zeit mit `expo` bleiben ungenutzt und laufen nach 90 Tagen ab.

## Prüfung

1. `curl -s localhost:8000/v1/config` liefert `{"pushProvider":"direct"}`.
2. In der Tabelle `device` stehen nach dem Login Tokens mit `provider = direct` (iOS: 64 Hex-Zeichen, Android: FCM-Token).
3. Als Moderator ein favorisiertes Fest absagen: Push „Fest abgesagt“ auf iOS und Android.
4. Im Worker-Log keine Meldungen `push_failed`, `apns_rejected` oder `fcm_rejected`. `apns_rejected` mit `BadDeviceToken` deutet auf eine falsche `APNS_SANDBOX`-Einstellung hin.

## Rollback

`PUSH_PROVIDER=expo` oder `disabled` setzen und API und Worker neu starten. Den APNs-Schlüssel im Apple-Konto und den Dienstkonto-Schlüssel in Firebase widerrufen, wenn sie nicht mehr gebraucht werden.
