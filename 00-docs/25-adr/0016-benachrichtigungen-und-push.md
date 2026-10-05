# 0016 · Benachrichtigungen als eigener Kontext, Push über Expo oder direkt über APNs und FCM

- **Status:** angenommen
- **Datum:** 2026-10-06

## Kontext

R11 bringt Benachrichtigungen: eine Liste in der App, Einstellungen je Art und Push-Mitteilungen. Auslöser kommen aus mehreren Kontexten: Veröffentlichen, Ändern und Absagen aus `moderation`, Favoriten aus `collections`, KI-Suchen aus `ai_ingestion`. Ab R12–R14 kommen Freunde, Listen und Einladungen dazu. CLAUDE.md nennt bisher vier Kontexte.

Für Push gibt es zwei Wege: über den Expo Push Service (USA), der an Apple (APNs) und Google (FCM) weiterleitet, oder direkt vom Backend an APNs und FCM. APNs und FCM sind für Push auf iOS und Android unvermeidbar. CLAUDE.md verlangt, dass Nicht-EU-Verarbeiter per ENV abschaltbar sind und keine personenbezogenen Daten erhalten.

## Entscheidung

1. **Fünfter Kontext `notifications`** (`domain/`, `application/`, Adapter unter `adapters/outbound/persistence/notifications.py` und `adapters/outbound/push/`). Andere Kontexte liefern nur Domain-Events über die Outbox (ADR 0005); der Kontext liest Favoriten und Wohnorte über den Port `Recipients` und den Starter einer KI-Suche über `AiSearchOwners`. Kein Kontext schreibt in die Tabellen eines anderen.
2. **Liste immer, Push nur bei aktivierter Art.** Jede Benachrichtigung wird gespeichert, die Einstellungen steuern nur den Push. Gespeichert werden Art und IDs (E-09); der Text entsteht beim Lesen.
3. **Push-Port mit drei Adaptern**, gewählt per `PUSH_PROVIDER`, ohne Code-Änderung:
   - `expo`: Expo Push Service (`EXPO_ACCESS_TOKEN`). Tickets mit `DeviceNotRegistered` entfernen das Gerät sofort, die Receipts prüft ein Job 15 Minuten später.
   - `direct`: APNs (Token-Authentifizierung mit `.p8`-Schlüssel, nur HTTP/2, dafür das Paket `h2`) und FCM HTTP v1 (Dienstkonto, OAuth-Token per signiertem JWT mit dem vorhandenen `pyjwt`). Für beide Plattformen gleich, keine Sonderwege je Betriebssystem.
   - `disabled`: kein Push (Standard lokal und in Tests).
   Fehlende Zugangsdaten für den gewählten Anbieter beenden den Start.
4. **Push-Inhalt ohne Personenbezug (E-04):** generischer Titel und Text je Art, dazu nur `type`, `notificationId`, `targetType`, `targetId` und die Zahl ungelesener Einträge als Badge.
5. **Zustellung:** Domain-Event bzw. Zeitplan → Empfänger → Einträge in Blöcken zu 500 → je Block ein Push-Job (arq). Ein nicht erreichbarer Push-Dienst führt zu bis zu 5 Versuchen mit wachsendem Abstand.

## Datenschutz

- Expo (650 Industries, Inc., USA), Apple (APNs) und Google (FCM) erhalten Push-Token, generische Texte und IDs. Push-Token sind pseudonyme Gerätekennungen; Namen, Festnamen, Orte oder Wohnorte gehen nie an die Push-Dienste (Test `test_push_texts_are_generic`, `test_push_respects_settings_and_carries_ids_only`).
- APNs und FCM sind für Push auf iOS und Android unvermeidbar. Mit `direct` entfällt Expo als zusätzlicher Verarbeiter; mit `disabled` gehen keine Daten an Push-Dienste.
- Vor dem Produktivstart: Datenschutzbedingungen von Expo, Apple und Google prüfen und im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) auf „aktiv“ setzen.

## Konsequenzen

- CLAUDE.md und die Systemarchitektur nennen fünf Kontexte.
- R12–R14 registrieren ihre Arten (`friend_added`, `list_added`, `invite`, `rsvp_*`) im selben Mechanismus: neue Werte in `NotificationType`, Textvorlagen, Einstellungsschalter und je ein Auslöser im Consumer.
- Neue Abhängigkeiten: `h2` (über `httpx[http2]`) im Backend, `expo-notifications` in der App.

## Verworfene Alternativen

- **Benachrichtigungen im Kontext `collections`:** Der Kontext würde Moderations- und KI-Ereignisse verarbeiten, die mit Favoriten nichts zu tun haben.
- **Nur Expo:** einfacher, lässt aber keinen Weg ohne zusätzlichen US-Verarbeiter.
- **`direct` nur für Android:** spart `h2`, behandelt iOS aber anders als Android.
- **Google-Bibliothek `google-auth` für FCM:** eine weitere Abhängigkeit für etwas, das `pyjwt` schon kann.
