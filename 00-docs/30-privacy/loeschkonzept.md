# Löschkonzept

> Stand R05: Nutzerkonto (`app_user`). Jedes Inkrement mit Personenbezug erweitert Tabelle, `SqlUserRepository.delete_personal_data` und Tests im selben PR.

## Aufbewahrung und Löschung je Datenart

| Datenart (Tabelle) | Personenbezug | Aufbewahrung | Löschweg | Test | Inkrement |
|---|---|---|---|---|---|
| Nutzerkonto (`app_user`) | IdP-Subject, Vor- und Nachname | bis zur Kontolöschung | `DeleteAccount`, Schritt 1 | `test_identity_use_cases.py`, `test_accounts.py` | R05 |
| Audit-Felder (`event.created_by`, `event.updated_by`) | Verweis auf die Nutzer-ID eines Moderators | bis zur Kontolöschung | `DeleteAccount`, Schritt 1: auf `null` | `test_accounts.py` | R05 |
| Konto beim IdP (Zitadel/Keycloak) | E-Mail, Name, Anmeldedaten, Rollen, Region | bis zur Kontolöschung | `DeleteAccount`, Schritt 2 (IdP-Admin-Port, ADR 0010) | `test_idp_admin_adapters.py`, `test_keycloak_login.py` | R05 |
| Retry-Job `delete_idp_user` (Redis) | IdP-Subject im Job | bis zum Erfolg, höchstens ca. 2 Tage (15 Versuche) | automatisch nach Ausführung | `test_worker_jobs.py` | R05 |
| Tokens (App, Secure Store) | Access-, Refresh-, ID-Token | bis zum Abmelden bzw. Ablauf | Abmelden, Kontolöschung, abgelehnte Erneuerung | `AuthProvider.test.tsx` | R05 |

## Kontolöschung (R05)

Auslöser: „Konto löschen“ auf der Konto-Seite der App → Dialog „Konto endgültig löschen?“ → `DELETE /v1/me` (`204`). Use Case `DeleteAccount` (`application/identity/use_cases.py`):

1. **Lokale Daten:** `SqlUserRepository.delete_personal_data` löscht in **einer Transaktion** den Eintrag in `app_user` und setzt `created_by`/`updated_by` aller Feste mit dieser Nutzer-ID auf `null`. Spätere Inkremente ergänzen hier ihre Tabellen (Favoriten R06, Geräte R11, Freunde R12, Listen R13, Einladungen R14).
2. **IdP:** Der IdP-Admin-Port löscht den Nutzer beim IdP (Zitadel User API v2, lokal Keycloak Admin API). Ist der Nutzer dort schon weg (`404`), gilt das als Erfolg.
3. **Retry:** Ist der IdP nicht erreichbar, reiht der Use Case den arq-Job `delete_idp_user` ein (Job-ID `delete_idp_user:<subject>`, doppelte Anfragen werden zusammengefasst). Der Worker versucht es mit wachsenden Abständen (1, 2, 4 … Minuten, höchstens 6 Stunden) bis zu 15-mal, also etwa zwei Tage lang. Scheitert auch der letzte Versuch, loggt der Worker `idp_deletion_failed` mit der Job-ID; der Nutzer wird dann von Hand gelöscht ([Zitadel-Anleitung](../40-operations/zitadel.md#nutzer-von-hand-löschen)).
4. Lässt sich auch der Job nicht einreihen (Redis weg), antwortet die API mit `503`. Die lokalen Daten sind dann schon gelöscht; die App bietet erneut „Löschen“ an, und die Wiederholung ist unschädlich.
5. Die App löscht danach die lokalen Tokens, schließt alle Seiten und zeigt „Dein Konto wurde gelöscht“.

Hinweis: Bis zum Ablauf des Access-Tokens (5 min) könnte ein erneuter `GET /v1/me` das Konto wieder anlegen. Die App meldet sich deshalb sofort lokal ab.

## Backups

Wirkung von Löschungen auf Backups: folgt in R16 (Ablauf der Backup-Aufbewahrung).
