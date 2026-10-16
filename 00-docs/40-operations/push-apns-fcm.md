# Push direkt über APNs und FCM einrichten

## Zweck

Mit `PUSH_PROVIDER=direct` (Produktion, [ADR 0019](../25-adr/0019-produktionsstack.md)) sendet das Backend selbst an Apple (APNs, iOS) und Google (FCM HTTP v1, Android). Expo fällt als zusätzlicher Verarbeiter weg ([ADR 0016](../25-adr/0016-benachrichtigungen-und-push.md)). Die App registriert dann das native Geräte-Token (`getDevicePushTokenAsync`).

## Voraussetzungen

- Apple-Developer-Programm (Rolle Admin); die App-ID `de.stadtfestfinder.app` legt EAS beim ersten iOS-Build an, inklusive der Capability „Push Notifications“ ([eas-build.md](eas-build.md))
- Google-Konto für die [Firebase-Konsole](https://console.firebase.google.com)
- Admin-Zugang zu Komodo (Variablen)

### Werte, die in dieser Anleitung entstehen

| Wert | entsteht in | wird eingetragen in |
|---|---|---|
| APNs-Schlüssel `AuthKey_<KEYID>.p8` | Schritt 1 | base64 → Komodo-Variable `STADTFEST_APNS_KEY_BASE64` (**secret**) |
| Key-ID des APNs-Schlüssels | Schritt 1 | Komodo-Variable `STADTFEST_APNS_KEY_ID` |
| Apple-Team-ID | Schritt 1 | Komodo-Variable `STADTFEST_APPLE_TEAM_ID` (auch für Universal Links) |
| Firebase-Projekt-ID | Schritt 2 | Komodo-Variable `STADTFEST_FCM_PROJECT_ID` |
| Dienstkonto-Schlüssel (JSON) | Schritt 2 | base64 → Komodo-Variable `STADTFEST_FCM_CREDENTIALS_BASE64` (**secret**) |
| `google-services.json` | Schritt 2 | `mobile/google-services.json` im Repo (enthält nur öffentliche Kennungen) |

## Schritte

1. **APNs-Schlüssel:** [developer.apple.com](https://developer.apple.com/account/resources/authkeys/list) → *Keys* → „+“ → Name „Stadtfest-Finder Push“, **Apple Push Notifications service (APNs)** aktivieren → *Continue* → *Register* → **Download** (`AuthKey_<KEYID>.p8`, nur einmal möglich). Die **Key ID** steht beim Schlüssel, die **Team ID** unter *Membership*.
   ```bash
   base64 -i AuthKey_<KEYID>.p8 | tr -d '\n'     # → STADTFEST_APNS_KEY_BASE64
   ```
2. **Firebase / FCM:**
   1. [Firebase-Konsole](https://console.firebase.google.com) → *Projekt hinzufügen* (z. B. `stadtfest`, Google Analytics **aus**). Die **Projekt-ID** steht unter *Projekteinstellungen → Allgemein*.
   2. *Projektübersicht → App hinzufügen → Android*, Paketname `de.stadtfestfinder.app` → `google-services.json` herunterladen. Liegt im Repo schon eine `mobile/google-services.json`, prüfen, dass ihr `project_id` dieselbe Projekt-ID ist; sonst die Datei ersetzen (per PR) und die App neu bauen.
   3. *Projekteinstellungen → Dienstkonten → Neuen privaten Schlüssel generieren* → JSON-Datei. Sie enthält einen privaten Schlüssel: **nie** ins Repo, nach dem Eintragen löschen.
   ```bash
   base64 -i stadtfest-firebase-adminsdk-xxxx.json | tr -d '\n'   # → STADTFEST_FCM_CREDENTIALS_BASE64
   ```
3. **Komodo-Variablen** anlegen (*Settings → Variables*, [deployment-komodo.md](deployment-komodo.md), Schritt 4): `STADTFEST_APNS_KEY_ID`, `STADTFEST_APPLE_TEAM_ID`, `STADTFEST_FCM_PROJECT_ID` als normale Variablen, `STADTFEST_APNS_KEY_BASE64` und `STADTFEST_FCM_CREDENTIALS_BASE64` als *Secret*. Fest im HomeLab gesetzt sind `PUSH_PROVIDER=direct`, `APNS_TOPIC=de.stadtfestfinder.app`, `APNS_SANDBOX=false`.
4. Stack `stadtfest` in Komodo neu deployen. Fehlt ein Wert oder ist der base64-Text bzw. das JSON ungültig, bricht der Start mit dem Namen der Variable ab (nie mit dem Wert).
5. Die App meldet sich nach dem nächsten Start bzw. Login mit dem nativen Token an (`GET /v1/config` liefert `direct`).

`APNS_SANDBOX=false` gilt für TestFlight-, Ad-hoc- (`preview`) und Store-Builds. Nur Development-Builds (Xcode, EAS-Profil `development`) brauchen die Sandbox; dafür lokal `APNS_SANDBOX=true` setzen.

**Lokal** (`.env`) gehen statt base64 auch Dateipfade: `APNS_KEY_PATH=/pfad/AuthKey.p8`, `FCM_CREDENTIALS_PATH=/pfad/dienstkonto.json` (siehe `.env.example`).

## Prüfung

1. `curl -s https://stadtfest-api.herderstreet.de/v1/config` liefert `{"pushProvider":"direct"}`.
2. In der Tabelle `device` stehen nach dem Login Tokens mit `provider = direct` (iOS: 64 Hex-Zeichen, Android: FCM-Token).
3. Als Moderator ein favorisiertes Fest absagen: Push „Fest abgesagt“ auf iOS und Android.
4. In Grafana keine Meldungen `push_failed`, `apns_rejected` oder `fcm_rejected` (`{container="stadtfest-worker"} | json`). `apns_rejected` mit `BadDeviceToken` deutet auf eine falsche `APNS_SANDBOX`-Einstellung hin.

## Rollback

`PUSH_PROVIDER=disabled` (im HomeLab `resources.toml`, PR) bzw. `expo` ([push-expo.md](push-expo.md)) setzen und neu deployen. Den APNs-Schlüssel im Apple-Konto und den Dienstkonto-Schlüssel in Firebase widerrufen, wenn sie nicht mehr gebraucht werden; bei einem kompromittierten Schlüssel neuen erzeugen und die Secret-Variable ersetzen.
