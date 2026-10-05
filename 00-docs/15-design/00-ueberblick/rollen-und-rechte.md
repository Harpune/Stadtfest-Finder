# Rollen und Rechte

Es gibt drei Rollen. Moderatoren melden sich mit demselben Account an wie normale Nutzer. Die Rolle ist eine Eigenschaft des Accounts (`roles: ["user","moderator"]`). Regionen gibt es nicht mehr: Die Rolle gilt für alle Feste in Deutschland ([ADR 0015](../../25-adr/0015-regionen-abgeschafft.md)).

| Funktion | Gast | Nutzer | Moderator |
|---|---|---|---|
| Karte, Liste, Suche, Filter | ✓ | ✓ | ✓ |
| Detailseite, Route starten, Website öffnen | ✓ | ✓ | ✓ |
| Favorit markieren | Hinweis → Login | ✓ | ✓ |
| Fest teilen | Hinweis → Login | ✓ | ✓ |
| Freunde einladen, zu-/absagen | Hinweis → Login | ✓ | ✓ |
| Gemeinsame Listen | – | ✓ | ✓ |
| Benachrichtigungen und Einstellungen | – | ✓ | ✓ |
| Profil-Drawer mit Zeitleiste | Anmelde-Hinweis | ✓ | ✓ |
| Link „Moderator-Ansicht“ im Drawer | – | – | ✓ |
| Feste anlegen, bearbeiten, veröffentlichen, absagen, löschen | – | – | ✓ alle Feste |
| KI-Suche per PLZ auslösen | – | – | ✓ für jede PLZ |
| Kategorien anlegen, bearbeiten, sortieren, deaktivieren, löschen | – | – | ✓ app-weit |
| Nutzer verwalten | – | – | – (ausdrücklich nicht vorgesehen) |

## Durchsetzung

- Das **Frontend** blendet Moderationsfunktionen nur ein, wenn `GET /v1/me` die Rolle `moderator` liefert.
- Das **Backend** prüft jede Anfrage unter `/v1/mod/*` selbst: Rolle vorhanden. Verstöße ergeben `403`, unbekannte Feste `404`.
- Gast-Aufrufe an geschützte Endpunkte ergeben `401`. Der Client zeigt daraufhin den Gast-Hinweis ([03](../workflows/03-authentifizierung.md)).

## Screenshots

| Nutzer (ohne Moderator-Link) | Moderator (mit Moderator-Link) | Moderationsansicht |
|---|---|---|
| <img src="../screenshots/04-04-drawer-ohne-moderator.png" width="220"> | <img src="../screenshots/04-01-drawer-zeitleiste.png" width="220"> | <img src="../screenshots/08-01-mod-feste.png" width="220"> |

## Offene Punkte

- Darf jeder Moderator Kategorien ändern, oder nur eine eigene Rolle „Kategorie-Admin“? Der Prototyp erlaubt es jedem Moderator.
- Wer vergibt die Moderator-Rolle? Ein Admin beim IdP (E-07, [Moderator einrichten](../../40-operations/moderator-einrichten.md)).
