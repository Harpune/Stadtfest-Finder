# 0007 · SeaweedFS als S3-kompatibler Objektspeicher

- **Status:** angenommen
- **Datum:** 2026-09-28

## Kontext

CLAUDE.md sah MinIO als lokalen Objektspeicher für Festbilder vor. MinIO veröffentlicht seit 2025 keine Community-Docker-Images mehr: `minio/minio` und `quay.io/minio/minio` sind nicht mehr abrufbar (geprüft am 28.09.2026).

## Entscheidung

- **SeaweedFS** (Apache-2.0-Lizenz, Image `chrislusf/seaweedfs`, feste Version) ersetzt MinIO lokal und in Tests. Es ist auch Kandidat für den Heimserver (Entscheidung in R16).
- Das Backend spricht ausschließlich die **S3-API** über den Storage-Port an. Ein Wechsel des S3-Anbieters braucht keine Codeänderung.
- **Lokal** gibt es eine Identität `stadtfest-dev` mit vollen Rechten und anonymes Lesen nur auf `stadtfest-images/public/` (für R08).

## Konsequenzen

- CLAUDE.md nennt statt MinIO jetzt SeaweedFS.
- Integrationstests für Bilder (R08) laufen gegen einen SeaweedFS-Testcontainer.

## Verworfene Alternativen

- **Garage** (Deuxfleurs, AGPL): sehr leichtgewichtig, aber ohne Bucket-Policies (öffentliches Lesen nur über den Website-Endpunkt) und mit mehr Setup.
- **MinIO aus Quellcode bauen:** unklare Sicherheitsupdates, eigener Pflegeaufwand.
