# 0010 · IdP-Admin-Port für die Kontolöschung

- **Status:** angenommen
- **Datum:** 2026-09-29
- **Bezug:** R05-US6, ADR 0003, [Löschkonzept](../30-privacy/loeschkonzept.md)

## Kontext

Nutzer können ihr Konto in der App löschen (Art. 17 DSGVO, App-Store-Pflicht). Die Anmeldedaten, die E-Mail-Adresse und die Verknüpfung mit Apple/Google liegen nicht im Backend, sondern beim IdP (Zitadel, lokal Keycloak). Eine Kontolöschung ist erst vollständig, wenn auch der IdP-Nutzer gelöscht ist. Der IdP kann dabei kurzzeitig nicht erreichbar sein.

## Entscheidung

- Ein Outbound-Port **`IdpAdminPort.delete_user(subject)`** in `application/identity/ports.py`. Adapter in `adapters/outbound/auth/idp_admin.py`, Auswahl per `IDP_ADMIN_PROVIDER`:
  - `zitadel` (Produktion): User API v2, `DELETE /v2/users/{id}` mit dem Personal Access Token eines Service-Users (`IDP_ADMIN_TOKEN`).
  - `keycloak` (lokal): Admin API, `DELETE /admin/realms/{realm}/users/{id}` mit einem vertraulichen Client im Client-Credentials-Grant (`IDP_ADMIN_CLIENT_ID`, `IDP_ADMIN_CLIENT_SECRET`).
  - `fake`: tut nichts; nur in `dev`/`test` erlaubt, der Start in `prod` schlägt fehl.
- Die IdP-Nutzer-ID ist der `sub`-Claim. `404` gilt als Erfolg (Löschung ist idempotent).
- **Sperre gegen das Wiederanlegen:** Vor allem anderen merkt sich die API den gehashten `sub` in Redis (Port `DeletedAccounts`), bis das Access-Token des Aufrufers abgelaufen ist. `Authenticate` lehnt Tokens gesperrter Konten mit `401` ab. Fällt Redis aus, gilt die Sperre nicht (fail open), damit ein Redis-Ausfall nicht alle Angemeldeten aussperrt.
- **Reihenfolge:** Erst werden die lokalen Daten in einer Transaktion gelöscht, dann der IdP-Nutzer. Schlägt der IdP-Aufruf fehl, reiht der Use Case den arq-Job `delete_idp_user` ein, der mit wachsenden Abständen bis zu 15-mal wiederholt.
- Der Job ist ein direktes Enqueue, keine Outbox (ADR 0005 folgt in R07). Kann er nicht eingereiht werden, antwortet die API mit `503` und die App lässt den Nutzer erneut löschen.

## Konsequenzen

- Der Service-User braucht Rechte zum Löschen von Nutzern (Zitadel: `ORG_USER_MANAGER`). Das Token ist ein Secret in Komodo und wird regelmäßig rotiert ([Anleitung](../40-operations/zitadel.md)).
- Tests nutzen einen Fake; ein Integrationstest prüft die Keycloak-Löschung gegen einen echten Container.
- Scheitert die Löschung dauerhaft, loggt der Worker `idp_deletion_failed` mit der Job-ID (enthält das IdP-Subject), und der Nutzer wird von Hand gelöscht.

## Verworfene Alternativen

- **Nur lokal löschen und den IdP-Nutzer stehen lassen:** unvollständige Löschung, der Nutzer könnte sich wieder anmelden und bekäme ein leeres Konto.
- **Selbstlöschung beim IdP mit dem Token des Nutzers (App → Zitadel):** bräuchte die Zitadel-API in der Audience des App-Tokens, liefe am Backend vorbei und ließe die lokalen Daten ohne Webhook stehen.
- **Zuerst IdP, dann lokal:** Bei einem Fehler zwischen den Schritten blieben personenbezogene Daten im Backend ohne Konto zurück.
