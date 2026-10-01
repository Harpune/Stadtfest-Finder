# Löschkonzept

> Stand R06: Nutzerkonto (`app_user`) und Favoriten (`favorite`). Jedes Inkrement mit Personenbezug erweitert Tabelle, `SqlUserRepository.delete_personal_data` und Tests im selben PR.

## Aufbewahrung und Löschung je Datenart

| Datenart (Tabelle) | Personenbezug | Aufbewahrung | Löschweg | Test | Inkrement |
|---|---|---|---|---|---|
| Nutzerkonto (`app_user`) | IdP-Subject, Vor- und Nachname | bis zur Kontolöschung | `DeleteAccount`, Schritt 1 | `test_identity_use_cases.py`, `test_accounts.py` | R05 |
| Audit-Felder (`event.created_by`, `event.updated_by`) | Verweis auf die Nutzer-ID eines Moderators | bis zur Kontolöschung | `DeleteAccount`, Schritt 1: auf `null` | `test_accounts.py` | R05 |
| Favoriten (`favorite`) | Nutzer-ID, Fest-ID, Zeitpunkt | bis zum Entfernen oder zur Kontolöschung; Vorschlag 24 Monate nach Festende (Job ab R11) | `DELETE /v1/me/favorites/{id}`; `DeleteAccount`, Schritt 1: `favorite_count` der betroffenen Feste wird verringert, die Zeilen löscht `ON DELETE CASCADE` | `test_favorites.py` | R06 |
| Konto beim IdP (Zitadel/Keycloak) | E-Mail, Name, Anmeldedaten, Rollen, Region | bis zur Kontolöschung | `DeleteAccount`, Schritt 2 (IdP-Admin-Port, ADR 0010) | `test_idp_admin_adapters.py`, `test_keycloak_login.py` | R05 |
| Retry-Job `delete_idp_user` (Redis) | IdP-Subject im Job | bis zum Erfolg, höchstens ca. 2 Tage (15 Versuche) | automatisch nach Ausführung | `test_worker_jobs.py` | R05 |
| Sperrvermerk gelöschter Konten (Redis, `sf:deleted:<hash>`) | SHA-256-Hash des IdP-Subjects | Restlaufzeit des letzten Access-Tokens plus Toleranz (`AUTH_LEEWAY_SECONDS`) | automatischer Ablauf (Redis-TTL) | `test_identity_use_cases.py`, `test_deleted_accounts.py` | R05 |
| Tokens (App, Secure Store) | Access-, Refresh-, ID-Token | bis zum Abmelden bzw. Ablauf | Abmelden, Kontolöschung, abgelehnte Erneuerung | `AuthProvider.test.tsx` | R05 |

## Kontolöschung (R05)

Auslöser: „Konto löschen“ auf der Konto-Seite der App → Dialog „Konto endgültig löschen?“ → `DELETE /v1/me` (`204`). Use Case `DeleteAccount` (`application/identity/use_cases.py`):

0. **Token sperren:** Zuerst merkt sich die API den gehashten IdP-Subject in Redis, bis das Access-Token des Aufrufers abgelaufen ist (plus Toleranz). Solange lehnt sie jedes Token dieses Kontos mit `401` ab. So legt ein paralleler oder späterer Aufruf mit dem noch gültigen Token (z. B. `GET /v1/me`) das Konto nicht wieder an. Ist Redis nicht erreichbar, läuft die Löschung trotzdem weiter (Warnung `deleted_accounts_unavailable` im Log).
1. **Lokale Daten:** `SqlUserRepository.delete_personal_data` löscht in **einer Transaktion** den Eintrag in `app_user` und setzt `created_by`/`updated_by` aller Feste mit dieser Nutzer-ID auf `null`. Die Favoriten (R06) entfernt `ON DELETE CASCADE`; vorher wird `favorite_count` der betroffenen Feste verringert. Spätere Inkremente ergänzen hier ihre Tabellen (Geräte R11, Freunde R12, Listen R13, Einladungen R14).
2. **IdP:** Der IdP-Admin-Port löscht den Nutzer beim IdP (Zitadel User API v2, lokal Keycloak Admin API). Ist der Nutzer dort schon weg (`404`), gilt das als Erfolg.
3. **Retry:** Ist der IdP nicht erreichbar, reiht der Use Case den arq-Job `delete_idp_user` ein (Job-ID `delete_idp_user:<subject>`, doppelte Anfragen werden zusammengefasst). Der Worker versucht es mit wachsenden Abständen (1, 2, 4 … Minuten, höchstens 6 Stunden) bis zu 15-mal, also etwa zwei Tage lang. Scheitert auch der letzte Versuch, loggt der Worker `idp_deletion_failed` mit der Job-ID; der Nutzer wird dann von Hand gelöscht ([Zitadel-Anleitung](../40-operations/zitadel.md#nutzer-von-hand-löschen)).
4. Lässt sich auch der Job nicht einreihen (Redis weg), antwortet die API mit `503`. Die lokalen Daten sind dann schon gelöscht; die App bietet erneut „Löschen“ an, und die Wiederholung ist unschädlich.
5. Die App löscht danach die lokalen Tokens, schließt alle Seiten und zeigt „Dein Konto wurde gelöscht“.

Hinweis: Die Sperre aus Schritt 0 gilt nur, solange Redis erreichbar ist. Fällt Redis aus, könnte ein noch gültiges Access-Token bis zu seinem Ablauf ein leeres Konto (nur Namen aus dem Token) wieder anlegen. Die App meldet sich deshalb zusätzlich sofort lokal ab.

## Backups

Wirkung von Löschungen auf Backups: folgt in R16 (Ablauf der Backup-Aufbewahrung).
