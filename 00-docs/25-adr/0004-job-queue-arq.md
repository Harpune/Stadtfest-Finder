# 0004 · arq auf Redis als Job-Queue

- **Status:** angenommen
- **Datum:** 2026-09-28

## Kontext

Hintergrundarbeit, die nicht Teil der Antwort ist, läuft asynchron: KI-Suche, Benachrichtigungs-Fan-out, Thumbnails, zeitgesteuerte Jobs. Das Backend ist async (FastAPI, SQLAlchemy async).

## Entscheidung

- **arq** (asyncio, Redis) als Queue und Worker. Redis dient zugleich als Cache.
- Der Worker ist ein eigener Prozess (`python -m stadtfest.bootstrap.worker`) mit derselben Composition Root wie die API.
- Cron-Jobs laufen in der Zeitzone `Europe/Berlin`.
- Job-Handler (`adapters/inbound/worker/`) sind dünn: Argumente parsen, Use Case aufrufen.

## Konsequenzen

- Jobs müssen idempotent sein: arq wiederholt fehlgeschlagene Jobs, und die Outbox (ADR 0005) kann ein Event mehrfach einreihen.
- Verlorene Queue-Einträge rekonstruiert die Outbox.

## Verworfene Alternativen

- Celery: synchron-orientiert, schwergewichtig.
- Dramatiq/RQ: kein natives asyncio.
