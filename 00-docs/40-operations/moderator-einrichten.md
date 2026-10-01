# Moderator einrichten

## Zweck

Moderatoren pflegen die Feste ihrer Region (E-07). Rolle und Region werden nicht in der App vergeben, sondern beim IdP: die Rolle `moderator` und das Nutzer-Metadatum `region`. Das Backend liest beides aus dem Access-Token (R05). Ohne gültige Region hat ein Moderator keine Moderationsrechte.

## Voraussetzungen

- Die Person hat sich mindestens einmal in der App angemeldet (dann existiert das Konto beim IdP).
- Zitadel: Rolle `ORG_USER_MANAGER` oder höher; eingerichtet nach [Zitadel einrichten](zitadel.md).
- Der Schlüssel der Region (z. B. `ostalb`) existiert in der Tabelle `region` (Seed bzw. Moderation).

## Schritte

### Produktion (Zitadel)

1. Konsole → *Benutzer* → Person suchen → *Autorisierungen* → *Neu* → Projekt `stadtfest`, Rolle **`moderator`** (für App-weite Kategorien zusätzlich `category_admin`).
2. Beim selben Nutzer → *Metadaten* → Schlüssel **`region`**, Wert = Regionsschlüssel, z. B. `ostalb`.
3. Die Person meldet sich in der App ab und wieder an (die Rolle gilt ab dem nächsten Token, spätestens nach 5 Minuten durch die stille Erneuerung).

### Lokal (Keycloak)

1. http://localhost:58080 → Admin `admin`/`admin` → Realm `stadtfest` → *Users* → Nutzer.
2. *Role mapping* → *Assign role* → `moderator`.
3. *Attributes* → `region` = `ostalb` → *Save*.
4. Der Testnutzer `moderator@example.test` (Passwort `stadtfest-dev`) ist bereits so eingerichtet.

## Prüfung

- In der App anmelden; `GET /v1/me` liefert `"roles": ["user", "moderator"]` und `"region": {"key": "ostalb", …}`.
- Fehlt die Region oder ist der Schlüssel unbekannt, fehlt `moderator` in `roles`, und das Backend loggt `moderator_without_region` bzw. `moderator_region_unknown` (ohne Nutzerdaten).

## Rollback

- Rolle `moderator` in den Autorisierungen entfernen und das Metadatum `region` löschen. Die Rechte enden mit dem nächsten Access-Token (spätestens nach 5 Minuten).
