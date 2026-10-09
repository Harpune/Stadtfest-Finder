# Löschkonzept

> Stand R12: Nutzerkonto (`app_user`), Favoriten (`favorite`), Upload-Slots (`upload`), Festbilder, KI-Suchaufträge (`ai_search_job`), Benachrichtigungen (`notification`), Einstellungen (`notification_settings`) Push-Geräte (`device`), Freundschaften (`friendship`) und Freundschaftslinks (`friend_link`). Jedes Inkrement mit Personenbezug erweitert Tabelle, `SqlUserRepository.delete_personal_data` und Tests im selben PR.

## Aufbewahrung und Löschung je Datenart

| Datenart (Tabelle) | Personenbezug | Aufbewahrung | Löschweg | Test | Inkrement |
|---|---|---|---|---|---|
| Nutzerkonto (`app_user`) | IdP-Subject, Vor- und Nachname | bis zur Kontolöschung | `DeleteAccount`, Schritt 1 | `test_identity_use_cases.py`, `test_accounts.py` | R05 |
| Audit-Felder (`event.created_by`, `event.updated_by`) | Verweis auf die Nutzer-ID eines Moderators | bis zur Kontolöschung | `DeleteAccount`, Schritt 1: auf `null` | `test_accounts.py` | R05 |
| Favoriten (`favorite`) | Nutzer-ID, Fest-ID, Zeitpunkt | bis zum Entfernen oder zur Kontolöschung; Vorschlag 24 Monate nach Festende (Job ab R11) | `DELETE /v1/me/favorites/{id}`; `DeleteAccount`, Schritt 1: `favorite_count` der betroffenen Feste wird verringert, die Zeilen löscht `ON DELETE CASCADE` | `test_favorites.py` | R06 |
| Upload-Slots (`upload`) | Nutzer-ID des Moderators, Dateityp, Größe, Zeitpunkt | bis zur Verarbeitung des Bildes; nie angehängte nach 24 h | nach erfolgreicher Verarbeitung (`mark_ready`); täglicher Job `purge_images` (03:45 Uhr); Kontolöschung: `ON DELETE CASCADE` | `test_images.py`, `test_image_use_cases.py` | R08 |
| Festbilder (`event_image`, Dateien unter `public/images/`) | keine Metadaten (entfernt); ggf. abgebildete Personen | bis zum Entfernen oder Löschen des Fests | `DELETE …/images/{id}` → `image.removed` löscht die Dateien; Bilder gelöschter Feste löscht `purge_images` | `test_images.py`, `test_pillow_processor.py` | R08 |
| Originaldateien (`uploads/`) | ggf. EXIF mit GPS-Position | bis zur Verarbeitung; fehlgeschlagene bis zum Entfernen bzw. 24 h, wenn nie angehängt | `ProcessImage` löscht sie; `purge_images`; Lifecycle-Regel im Bucket als Sicherheitsnetz | `test_images.py` | R08 |
| KI-Suchaufträge (`ai_search_job`) | Nutzer-ID des Moderators; das Protokoll enthält keine Nutzerdaten | Zeile unbegrenzt (Statistik); Protokoll-Inhalte (Suchanfragen, URLs) 90 Tage nach Abschluss | `DeleteAccount`, Schritt 1: `moderator_id` auf `null` (`ON DELETE SET NULL`); wöchentlicher Job `compact_ai_search_logs` (So 04:15) lässt nur Zähler stehen | `test_accounts.py`, `test_ai_search_use_cases.py` | R10 |
| Verworfene Quellen (`rejected_source`) | keiner: URL einer öffentlichen Seite | unbegrenzt, damit verworfene Funde nicht erneut vorgeschlagen werden | – | `test_ai_search.py` | R10 |
| Benachrichtigungen (`notification`) | Nutzer-ID, Art, Fest-ID bzw. Nutzer-ID des Auslösers (`friend_added`, R12), gelesen, Zeitpunkt | 12 Monate; Einträge gelöschter Feste werden sofort ausgeblendet und mit dem Fest gelöscht | Wischen in der Liste (`DELETE /v1/me/notifications/{id}`); täglicher Job `purge_notifications` (03:50 Uhr); Kontolöschung: `ON DELETE CASCADE` | `test_notifications.py`, `test_notification_use_cases.py` | R11 |
| Benachrichtigungs-Einstellungen (`notification_settings`) | Schalter, Radius, Wohnort (PLZ, Ortsname, PLZ-Mittelpunkt) | bis zur Änderung oder Kontolöschung | Wohnort entfernen in den Einstellungen; Kontolöschung: `ON DELETE CASCADE` | `test_notifications.py` | R11 |
| Push-Geräte (`device`) | Push-Token, Plattform, Anbieter, Zeitpunkte | bis zum Abmelden; ungültige Token sofort bzw. nach den Receipts; 90 Tage ohne Aktivität | `DELETE /v1/me/devices/{token}` beim Abmelden; Job `check_push_receipts`; Job `purge_notifications`; Kontolöschung: `ON DELETE CASCADE` | `test_notifications.py`, `test_push_adapters.py` | R11 |
| Freundschaften (`friendship`) | Nutzer-IDs beider Seiten, Zeitpunkt | bis zum Entfernen oder zur Kontolöschung | `DELETE /v1/me/friends/{id}` entfernt beide Richtungen; Kontolöschung: `ON DELETE CASCADE` auf beiden Spalten | `test_friends.py`, `test_friend_use_cases.py` | R12 |
| Freundschaftslink (`friend_link`) | Nutzer-ID, Token, Zeitpunkt | bis zum Zurücksetzen oder zur Kontolöschung | „Link zurücksetzen“ ersetzt den Token; Kontolöschung: `ON DELETE CASCADE` | `test_friends.py` | R12 |
| Rate-Limit Freundschaftslinks (Redis, `sf:limit:<hash>`) | Hash über die Nutzer-ID | 1 Stunde | automatischer Ablauf (Redis-TTL) | `test_friend_use_cases.py` | R12 |
| Outbox (`outbox`) | keiner: nur Fest-IDs und Feldnamen | 14 Tage nach Versand | täglicher Job `purge_outbox` (03:30 Uhr) | `test_moderation.py` | R07 |
| Konto beim IdP (Zitadel/Keycloak) | E-Mail, Name, Anmeldedaten, Rollen | bis zur Kontolöschung | `DeleteAccount`, Schritt 2 (IdP-Admin-Port, ADR 0010) | `test_idp_admin_adapters.py`, `test_keycloak_login.py` | R05 |
| Retry-Job `delete_idp_user` (Redis) | IdP-Subject im Job | bis zum Erfolg, höchstens ca. 2 Tage (15 Versuche) | automatisch nach Ausführung | `test_worker_jobs.py` | R05 |
| Sperrvermerk gelöschter Konten (Redis, `sf:deleted:<hash>`) | SHA-256-Hash des IdP-Subjects | Restlaufzeit des letzten Access-Tokens plus Toleranz (`AUTH_LEEWAY_SECONDS`) | automatischer Ablauf (Redis-TTL) | `test_identity_use_cases.py`, `test_deleted_accounts.py` | R05 |
| Tokens (App, Secure Store) | Access-, Refresh-, ID-Token | bis zum Abmelden bzw. Ablauf | Abmelden, Kontolöschung, abgelehnte Erneuerung | `AuthProvider.test.tsx` | R05 |

## Kontolöschung (R05)

Auslöser: „Konto löschen“ auf der Konto-Seite der App → Dialog „Konto endgültig löschen?“ → `DELETE /v1/me` (`204`). Use Case `DeleteAccount` (`application/identity/use_cases.py`):

0. **Token sperren:** Zuerst merkt sich die API den gehashten IdP-Subject in Redis, bis das Access-Token des Aufrufers abgelaufen ist (plus Toleranz). Solange lehnt sie jedes Token dieses Kontos mit `401` ab. So legt ein paralleler oder späterer Aufruf mit dem noch gültigen Token (z. B. `GET /v1/me`) das Konto nicht wieder an. Ist Redis nicht erreichbar, läuft die Löschung trotzdem weiter (Warnung `deleted_accounts_unavailable` im Log).
1. **Lokale Daten:** `SqlUserRepository.delete_personal_data` löscht in **einer Transaktion** den Eintrag in `app_user` und setzt `created_by`/`updated_by` aller Feste mit dieser Nutzer-ID auf `null`. `ai_search_job.moderator_id` setzt die Datenbank per `ON DELETE SET NULL` auf `null` (R10). Die Favoriten (R06) entfernt `ON DELETE CASCADE`; vorher wird `favorite_count` der betroffenen Feste verringert. Benachrichtigungen, Einstellungen und Push-Geräte (R11) entfernt ebenfalls `ON DELETE CASCADE`. Freundschaften (beide Richtungen), der Freundschaftslink und Benachrichtigungen, in denen der Nutzer Auslöser ist (R12), gehen ebenfalls per `ON DELETE CASCADE`. Spätere Inkremente ergänzen hier ihre Tabellen (Listen R13, Einladungen R14).
2. **IdP:** Der IdP-Admin-Port löscht den Nutzer beim IdP (Zitadel User API v2, lokal Keycloak Admin API). Ist der Nutzer dort schon weg (`404`), gilt das als Erfolg.
3. **Retry:** Ist der IdP nicht erreichbar, reiht der Use Case den arq-Job `delete_idp_user` ein (Job-ID `delete_idp_user:<subject>`, doppelte Anfragen werden zusammengefasst). Der Worker versucht es mit wachsenden Abständen (1, 2, 4 … Minuten, höchstens 6 Stunden) bis zu 15-mal, also etwa zwei Tage lang. Scheitert auch der letzte Versuch, loggt der Worker `idp_deletion_failed` mit der Job-ID; der Nutzer wird dann von Hand gelöscht ([Zitadel-Anleitung](../40-operations/zitadel.md#nutzer-von-hand-löschen)).
4. Lässt sich auch der Job nicht einreihen (Redis weg), antwortet die API mit `503`. Die lokalen Daten sind dann schon gelöscht; die App bietet erneut „Löschen“ an, und die Wiederholung ist unschädlich.
5. Die App löscht danach die lokalen Tokens, schließt alle Seiten und zeigt „Dein Konto wurde gelöscht“.

Hinweis: Die Sperre aus Schritt 0 gilt nur, solange Redis erreichbar ist. Fällt Redis aus, könnte ein noch gültiges Access-Token bis zu seinem Ablauf ein leeres Konto (nur Namen aus dem Token) wieder anlegen. Die App meldet sich deshalb zusätzlich sofort lokal ab.

## Backups

Wirkung von Löschungen auf Backups: folgt in R16 (Ablauf der Backup-Aufbewahrung).
