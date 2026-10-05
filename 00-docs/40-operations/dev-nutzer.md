# Dev-Nutzer (lokale Entwicklung)

Testkonten des lokalen Keycloak (Realm `stadtfest`, [ADR 0003](../25-adr/0003-identity-provider-zitadel.md)). Sie stehen in `infra/dev/keycloak/stadtfest-realm.json` und gelten **nur lokal**. In Produktion (Zitadel) gibt es sie nicht.

## App-Nutzer

| Nutzer | E-Mail (Anmeldung) | Passwort | Rollen | Wofür |
|---|---|---|---|---|
| Lena Beispiel | `nutzer@example.test` | `stadtfest-dev` | `user` | Favoriten, Zeitleiste, Konto (R05, R06) |
| Mia Moderatorin | `moderator@example.test` | `stadtfest-dev` | `user`, `moderator` | Alle Feste und Bilder pflegen, KI-Suche (R07, R08, R10); Kategorien nur lesen |
| Karl Kategorie | `katadmin@example.test` | `stadtfest-dev` | `user`, `moderator`, `category_admin` | Wie Mia, dazu Kategorien anlegen, sortieren, löschen (R09) |

**Anmelden in der App:** Profil oben rechts → „Anmelden“ → „Mit E-Mail anmelden“ → E-Mail und Passwort eingeben. Für ein anderes Konto: Profil → „Abmelden“, dann erneut anmelden.

## Administration

| Zugang | Adresse | Benutzer | Passwort | Wofür |
|---|---|---|---|---|
| Keycloak-Admin-Konsole | http://localhost:58080 (Realm `stadtfest`) | `admin` | `admin` | Rollen vergeben, Nutzer anlegen ([Moderator einrichten](moderator-einrichten.md)) |
| Service-Account `stadtfest-admin` | – (Client Credentials) | – | `IDP_ADMIN_CLIENT_SECRET` in `.env` | Nur das Backend: löscht Keycloak-Nutzer bei der Kontolöschung (R05, [ADR 0010](../25-adr/0010-idp-admin-port.md)) |

## Hinweise

- Voraussetzung ist der lokale Stack (`make dev`, Daten mit `make seed`). Auf einem echten Gerät müssen die Ports weitergeleitet sein: [Lokale Entwicklung](lokale-entwicklung.md).
- Rollen stehen im Access-Token. Nach einer Änderung in Keycloak gelten sie erst nach erneuter Anmeldung. Regionen gibt es nicht mehr ([ADR 0015](../25-adr/0015-regionen-abgeschafft.md)).
- Ein in der App gelöschtes Konto ist auch in Keycloak weg. Wiederherstellen: Keycloak-Container mit frischem Realm neu anlegen (`docker compose -f infra/compose.dev.yaml up -d --force-recreate keycloak`).
- Mit diesen Passwörtern nie echte Dienste einrichten.
