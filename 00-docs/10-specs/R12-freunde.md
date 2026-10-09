# R12 · Freunde

| | |
|---|---|
| **Ziel** | Nutzer verbinden sich per persönlichem Freundschaftslink oder QR-Code. Freundschaften sind die Grundlage für gemeinsame Listen (R13) und Einladungen (R14). |
| **Hängt ab von** | R11 (Benachrichtigung „Freund hinzugefügt“) |
| **Quellen** | Entscheidung E-02. Im Design **nicht gestaltet**: [05 offene Punkte](../15-design/workflows/05-gemeinsame-listen.md#offene-punkte), Datenmodell `Friendship`. |
| **Bounded Context** | `collections` |
| **Rollen** | Nutzer |

> **Designlücke:** Die Screens „Freunde“, „Freund hinzufügen (QR/Link)“ und „Freundschaftsanfrage annehmen“ fehlen im Design. Umsetzung im bestehenden Design-System (Unterseite wie „Gemeinsame Listen“, Sheet wie „Neue Liste“). Die fertigen Screens kommen per Screenshot nach `15-design/screenshots/` (IDs `11-xx`).

## Umfang

**Drin:** Persönlicher Freundschaftslink (erneuerbar), QR-Anzeige, Link öffnen und annehmen (auch als Gast mit anschließendem Login), Freundesliste, Freund entfernen, Benachrichtigung an den Link-Inhaber.

**Nicht drin:** Suche nach Nutzern, Adressbuch-Abgleich, Freundschaftsanfragen mit Ablehnen. Der Link selbst ist die Zustimmung des Inhabers.

## User Stories

### R12-US1 · Eigenen Freundschaftslink teilen
- Drawer → „Freunde“ → Unterseite mit „Freund hinzufügen“.
- Das Sheet zeigt einen QR-Code und „Link teilen“ (natives Share-Sheet) mit Text „Werde mein Freund im Stadtfest-Finder: {url}“.
- `GET /v1/me/friend-link` → `{url, token, createdAt}`. Ohne Link wird einer angelegt.
- URL: `https://stadtfest-finder.de/freund/{token}`. Der Token hat 128 Bit Zufall (base64url) und **keinen Personenbezug** in der URL.
- `POST /v1/me/friend-link/rotate` → neuer Token, der alte ist sofort ungültig („Link zurücksetzen“, mit Bestätigung).

### R12-US2 · Link öffnen und annehmen
- Deep Link `/freund/{token}` öffnet das Sheet „Freundschaft annehmen“.
- **Als Gast:** Gast-Hinweis mit Text „Melde dich an, um dich mit {…} zu verbinden“. Ohne Login ist der Name des Inhabers nicht sichtbar. `pendingAction {type: friend, token}` wird gemerkt und nach dem Login ausgeführt.
- **Angemeldet:**
  - `GET /v1/friend-links/{token}` → `{owner: {firstName, lastNameInitial}}` (`404` bei ungültigem oder rotiertem Token)
  - Das Sheet zeigt „{Vorname} {N.} möchte sich mit dir verbinden“ mit „Annehmen“ und „Ablehnen“
- „Annehmen“ → `POST /v1/friend-links/{token}/accept` → `201 {friend}`. Idempotent, wenn die Freundschaft schon besteht. `422 self_link` beim eigenen Link.
- „Ablehnen“ schließt das Sheet, nichts wird gespeichert.
- Toast „Du bist jetzt mit {Vorname} befreundet“.
- Der Link-Inhaber bekommt die Benachrichtigung `friend_added`: „{Vorname} {Nachname} ist jetzt mit dir befreundet“. Sie erscheint nur in der Liste, **ohne Push** (Annahme).
- **Rate-Limit:** 20 Link-Abfragen pro Nutzer und Stunde, sonst `429` (Schutz gegen Token-Raten).

### R12-US3 · Freundesliste
- `GET /v1/me/friends` → `[{id, firstName, lastName, since}]`, alphabetisch.
- Unterseite „Freunde“: Avatar (Initialen, Farben aus der Freunde-Palette, deterministisch aus der ID), Name, „+ Freund hinzufügen“.
- Leerzustand: „Noch keine Freunde · Teile deinen Link, damit sich Freunde mit dir verbinden.“
- Wischen bzw. Menü „Entfernen“ → Bestätigung → `DELETE /v1/me/friends/{userId}` → `204`. Die Freundschaft wird **beidseitig** entfernt, ohne Benachrichtigung.
- Bestehende gemeinsame Listen und Einladungen bleiben beim Entfernen erhalten (Annahme).

## Daten

- `friendship`: `user_id`, `friend_id`, `created_at`, symmetrisch gespeichert (zwei Zeilen), PK `(user_id, friend_id)`, Check `user_id <> friend_id`.
- `friend_link`: `user_id` (PK), `token` (unique), `created_at`. Der Token wird im Klartext gespeichert, damit der Link wiederholt angezeigt werden kann. Er gewährt nur das Befreunden und lässt sich jederzeit rotieren.

## Datenschutz

- Der Name des Link-Inhabers ist erst nach Login sichtbar und nur als Vorname + Initial.
- VVT „Freundschaften“: Zweck soziale Funktionen, Daten Nutzer-IDs, Löschung bei Entfernen oder Kontolöschung.
- `DeleteAccount` löscht Freundschaften (beide Richtungen) und den Freundschaftslink.

## Tests

- Unit: Annehmen (idempotent, eigener Link, rotierter Token), Entfernen beidseitig, Rate-Limit.
- Integration: Symmetrie in der DB, Cascade bei Kontolöschung.
- Contract: Freundes-Endpunkte.
- Maestro: Nutzer A teilt den Link → Nutzer B öffnet den Deep Link (Gast → Login → Annehmen) → beide sehen einander in der Freundesliste.

## Definition of Done

- [ ] Freundes-Screens gestaltet, umgesetzt und als Screenshots ergänzt.
- [ ] Deep Link `/freund/{token}` funktioniert beim Kalt- und Warmstart.
- [ ] VVT und `DeleteAccount` erweitert.

## Entscheidungen bei der Umsetzung

- **QR-Code:** `react-native-qrcode-svg` (über das vorhandene `react-native-svg`), freigegeben am 09.10.2026.
- **URL:** Die API liefert nur `{token, createdAt}`; die App baut die URL `https://{EXPO_PUBLIC_LINK_HOST}/freund/{token}` wie bei geteilten Festen. So gibt es nur eine Stelle für die Link-Domain. Der Android-Intent-Filter und die Caddy-Fallback-Seite kennen den Pfad `/freund/`.
- **Benachrichtigung:** `friend_added` speichert den Freund als `actor_user_id`; der Text „{Vorname} {Nachname} ist jetzt mit dir befreundet“ entsteht beim Lesen. Das Ereignis `friendship.created` geht über die Outbox (gleiche Transaktion wie die Freundschaft). Kein Push.
- **Rate-Limit:** Nachschlagen und Annehmen zählen gemeinsam (20 pro Nutzer und Stunde, `429 rate_limited`).

## Offene Punkte

- Soll ein Link nach einer Anzahl Annahmen oder nach Zeit automatisch ablaufen? Vorerst nicht, nur manuelles Rotieren.
