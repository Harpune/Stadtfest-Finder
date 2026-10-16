# 0022 · Öffentlicher Eingang über den Cloudflare Tunnel des HomeLab

- **Status:** vorgeschlagen (Entscheidung offen, siehe „Offene Punkte“)
- **Datum:** 2026-10-16

## Kontext

Das HomeLab öffnet keine Ports nach außen. Öffentliche Dienste (Vaultwarden, Immich, Feststadt …) laufen über einen Cloudflare Tunnel: `cloudflared` im HomeLab baut eine ausgehende Verbindung zu Cloudflare auf, Cloudflare beantwortet die Anfragen an `*.herderstreet.de` an seinem Rand und leitet sie durch den Tunnel an den HomeLab-Caddy weiter. Der Stadtfest-Finder braucht vier öffentliche Hosts ([ADR 0019](0019-produktionsstack.md)).

Dabei beendet Cloudflare die TLS-Verbindung des Clients an seinem Rand. Cloudflare (Cloudflare, Inc., USA) sieht damit jede Anfrage im Klartext: IP-Adresse, Access-Tokens im `Authorization`-Header, API-Antworten mit Namen von Freunden, Einladungstexten usw. CLAUDE.md verlangt für jeden Verarbeiter außerhalb der EU ein ADR und, wo möglich, eine Umschaltung auf eine EU-Option.

## Entscheidung (vorgeschlagen)

1. Die vier Hosts laufen wie die übrigen öffentlichen Dienste des HomeLab über den Cloudflare Tunnel, ohne Cloudflare Access.
2. Cloudflare wird als **Auftragsverarbeiter** geführt: Data Processing Addendum von Cloudflare (gilt mit den Nutzungsbedingungen), Übermittlung in die USA auf Grundlage des EU-U.S. Data Privacy Framework (Cloudflare ist zertifiziert) bzw. der Standardvertragsklauseln im DPA.
3. Keine Funktionen, die Inhalte speichern oder auswerten: kein Caching von API-Antworten (die Hosts liefern `Cache-Control` passend; Cloudflare cacht dynamische Antworten standardmäßig nicht), keine Web Analytics, keine Bot-Fight-Challenges auf `stadtfest-api.` und `stadtfest-mcp.` (würden die App blockieren).

## Offene Punkte (vor dem Produktivstart klären)

- **Bewertung durch den Verantwortlichen:** Ist Cloudflare als US-Verarbeiter mit Klartextzugriff für diese App akzeptabel? Alternativen wären
  - eine Portfreigabe 443 nur für diese Hosts direkt auf den HomeLab-Caddy (kein Drittanbieter, aber eine eingehende Öffnung, die das HomeLab bisher vermeidet),
  - ein EU-Tunnel bzw. Reverse Proxy bei einem EU-Hoster (z. B. kleiner VPS mit WireGuard zum HomeLab).
- Eintrag in die Datenschutzerklärung (Abschnitt Empfänger) nach der Entscheidung bestätigen.

## Konsequenzen

- Eintrag im [Verarbeiterverzeichnis](../30-privacy/auftragsverarbeiter.md) und in der Datenschutzerklärung (`infra/edge/public/datenschutz/`).
- Der Wechsel auf eine der Alternativen braucht keine Codeänderung: nur die Tunnel-Hostnamen durch DNS-Einträge bzw. den anderen Proxy ersetzen.
