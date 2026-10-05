# Moderator einrichten

## Zweck

Moderatoren pflegen alle Feste in Deutschland und starten die KI-Suche für beliebige PLZ (E-07, [ADR 0015](../25-adr/0015-regionen-abgeschafft.md): keine Regionen). Die Rolle wird nicht in der App vergeben, sondern beim IdP: die Rolle `moderator`. Das Backend liest sie aus dem Access-Token (R05).

## Voraussetzungen

- Die Person hat sich mindestens einmal in der App angemeldet (dann existiert das Konto beim IdP).
- Zitadel: Rolle `ORG_USER_MANAGER` oder höher; eingerichtet nach [Zitadel einrichten](zitadel.md).

## Schritte

### Produktion (Zitadel)

1. Konsole → *Benutzer* → Person suchen → *Autorisierungen* → *Neu* → Projekt `stadtfest`, Rolle **`moderator`** (für App-weite Kategorien zusätzlich `category_admin`).
2. Die Person meldet sich in der App ab und wieder an (die Rolle gilt ab dem nächsten Token, spätestens nach 5 Minuten durch die stille Erneuerung).
3. Ein früher gesetztes Metadatum `region` wird nicht mehr gebraucht und kann gelöscht werden.

### Lokal (Keycloak)

1. http://localhost:58080 → Admin `admin`/`admin` → Realm `stadtfest` → *Users* → Nutzer.
2. *Role mapping* → *Assign role* → `moderator`.
3. Der Testnutzer `moderator@example.test` (Passwort `stadtfest-dev`) ist bereits so eingerichtet.

### Kategorie-Admin (R09, E-06)

Kategorien gelten app-weit. Ändern dürfen sie nur Nutzer mit der Rolle **`category_admin`**; Moderatoren ohne diese Rolle sehen den Tab „Kategorien“ nur lesend.

1. Zitadel: beim Nutzer unter *Autorisierungen* zusätzlich die Rolle `category_admin` vergeben. Keycloak: *Role mapping* → `category_admin`.
2. Damit die Moderationsansicht erreichbar ist, braucht die Person außerdem `moderator`.
3. Lokal ist `katadmin@example.test` (Passwort `stadtfest-dev`) bereits Moderator und Kategorie-Admin.

## Prüfung

- In der App anmelden; `GET /v1/me` liefert `"roles": ["user", "moderator"]`. Das Banner der Moderationsansicht zeigt den Namen der Person.
- Kategorie-Admin: `roles` enthält zusätzlich `category_admin`; im Tab „Kategorien“ erscheinen „+ Neu“ und die Griffe zum Sortieren. Ohne die Rolle antworten schreibende Aufrufe von `/v1/mod/categories` mit `403`.

## Rollback

- Rolle `moderator` (bzw. `category_admin`) in den Autorisierungen entfernen. Die Rechte enden mit dem nächsten Access-Token (spätestens nach 5 Minuten).
