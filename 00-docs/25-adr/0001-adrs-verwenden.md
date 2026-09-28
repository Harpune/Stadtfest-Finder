# 0001 · Architekturentscheidungen als ADR festhalten

- **Status:** angenommen
- **Datum:** 2026-09-28

## Kontext

Der Stadtfest-Finder wird schrittweise gebaut (siehe [`10-specs`](../10-specs/README.md)). Entscheidungen zu Architektur, Abhängigkeiten und externen Diensten müssen nachvollziehbar bleiben, auch für KI-gestützte Entwicklung (CLAUDE.md verweist auf diesen Ordner).

## Entscheidung

Jede Entscheidung mit Architekturwirkung, jede neue externe Abhängigkeit mit Betriebs- oder Datenschutzwirkung und jeder Nicht-EU-Verarbeiter bekommt ein ADR in `00-docs/25-adr/NNNN-titel.md`.

**Aufbau:** Status, Datum, Kontext, Entscheidung, Konsequenzen, verworfene Alternativen.

**Status-Werte:** `vorgeschlagen`, `angenommen`, `abgelöst durch NNNN`, `verworfen`. Angenommene ADRs werden nicht umgeschrieben, sondern durch neue abgelöst.

## Konsequenzen

- Das ADR entsteht im selben PR wie die Änderung.
- Die Sprache ist Deutsch (wie alle Dokumente in `00-docs/`).

## Übersicht

| Nr. | Titel | Status |
|---|---|---|
| 0001 | Architekturentscheidungen als ADR festhalten | angenommen |
| 0002 | [Hexagonale Architektur und Bounded Contexts](0002-hexagonale-architektur.md) | angenommen |
| 0003 | [Zitadel als Identity Provider, Keycloak lokal](0003-identity-provider-zitadel.md) | angenommen |
| 0004 | [arq auf Redis als Job-Queue](0004-job-queue-arq.md) | angenommen |
| 0005 | [Domain-Events über Transactional Outbox](0005-transactional-outbox.md) | angenommen |
| 0006 | [Selbst gehostetes Nominatim für Geocoding](0006-geocoding-nominatim.md) | angenommen |
| 0007 | [SeaweedFS als S3-kompatibler Objektspeicher](0007-objektspeicher-seaweedfs.md) | angenommen |
| 0008 | [Codegen aus der OpenAPI-Spezifikation](0008-codegen-openapi.md) | angenommen |
