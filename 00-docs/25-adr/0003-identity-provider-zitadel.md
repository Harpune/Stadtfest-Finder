# 0003 · Zitadel als Identity Provider, Keycloak lokal

- **Status:** angenommen
- **Datum:** 2026-09-28
- **Bezug:** Entscheidungen E-01, E-06, E-07, E-08 in [`10-specs/README.md`](../10-specs/README.md)

## Kontext

Die App braucht Anmeldung per Apple, Google und E-Mail. Das Backend soll nie Passwörter verarbeiten (CLAUDE.md). Alle Verarbeiter müssen in der EU sitzen.

## Entscheidung

- **Produktion:** Zitadel Cloud, EU-Region.
- **Lokal und in Tests:** Keycloak (`infra/compose.dev.yaml`, Realm `infra/dev/keycloak/stadtfest-realm.json`).
- Die App meldet sich per OIDC Authorization Code + PKCE im **Hosted Login** an. Apple und Google sind als externe IdPs in Zitadel angebunden. Eigene `/auth/*`-Endpunkte gibt es nicht.
- **Rollen:** `user`, `moderator`, `category_admin`, vergeben in Zitadel.
- Die **Region** eines Moderators ist ein Nutzer-Metadatum und erscheint als Claim `region` im Access-Token.
- Die Claim-Namen sind konfigurierbar, weil sich Zitadel und Keycloak unterscheiden:

  | Claim | Keycloak | Zitadel |
  |---|---|---|
  | Rollen | `realm_access.roles` | `urn:zitadel:iam:org:project:roles` |
  | Region | Mapper `region` | per Action |

- **Audience** der API: `stadtfest-api`.
- Das Backend validiert JWTs gegen das JWKS des IdP und speichert keine E-Mail-Adressen (E-08).

## Konsequenzen

- Die Screens 03-04 bis 03-06 werden zu einem Einstieg-Screen, die Formulare liegen beim IdP.
- Die Kontolöschung braucht einen Service-User mit Management-API-Rechten (R05).
- Der lokale Realm enthält Testnutzer (nur Entwicklung) und einen Client `stadtfest-tests` mit Password-Grant ausschließlich für Integrationstests.

## Verworfene Alternativen

- Eigene Authentifizierung im Backend: widerspricht CLAUDE.md (keine Passwörter im Backend).
- Native Login-Formulare über die Zitadel Session API: näher am Design, aber aufwendiger und nicht reines PKCE.
