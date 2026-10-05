# 0013 · Web-Suche über selbst gehostetes SearXNG

- **Status:** angenommen
- **Datum:** 2026-10-02

## Kontext

Das Sprachmodell der KI-Suche (ADR 0012) braucht ein Werkzeug, um aktuelle Veranstaltungsseiten zu finden. Jeder Fund muss eine Quelle aus diesen Suchergebnissen tragen. Der Such-Anbieter soll unabhängig vom LLM-Anbieter sein und per ENV austauschbar. EU-Anbieter bzw. selbst gehostete Lösungen werden bevorzugt (CLAUDE.md „Privacy“), und die Suche soll ohne laufende Kosten auskommen.

Zuerst war die Brave Search API vorgesehen. Sie hat keinen kostenlosen Tarif (Entscheidung des Projektinhabers am 02.10.2026). Kostenlose Such-APIs (Tavily, Exa, Serper) sitzen in den USA und haben feste Kontingente.

## Entscheidung

- **SearXNG**, eine Open-Source-Metasuchmaschine, läuft als eigener Container auf dem eigenen Server (EU) und implementiert über `SearxngWebSearch` den Port `WebSearchPort` (`adapters/outbound/search/searxng.py`).
- Auswahl per ENV: `WEB_SEARCH_PROVIDER=searxng|brave|fake`. Für `searxng` ist `WEB_SEARCH_BASE_URL` Pflicht (z. B. `http://searxng:8080`). `fake` (feste Treffer) ist nur in `dev` und `test` erlaubt.
- Anfrage: `GET {WEB_SEARCH_BASE_URL}/search` mit `q`, `format=json`, `categories=general`, `language=de-DE`, `safesearch=2`. Der Adapter gibt nur URL, Titel und Snippet an das Modell weiter, höchstens so viele Treffer wie angefragt.
- Konfiguration in `settings.yml` (lokal `infra/dev/searxng/settings.yml`):
  - JSON-Ausgabe an (sonst `403`);
  - Limiter aus, weil die Instanz intern ist;
  - Tor-Engines und die Brave-Engine aus.

  Die Instanz ist nur im internen Netz erreichbar, nicht öffentlich.
- Liefert SearXNG keine Treffer, weil Engines ausfielen (z. B. CAPTCHA), endet der Job mit `search_unavailable` statt mit „keine Funde“. Es gibt keinen stillen Rückfall auf einen anderen Anbieter.
- **Brave Search API** bleibt als optionaler Adapter (`WEB_SEARCH_PROVIDER=brave`, `WEB_SEARCH_API_KEY`). Brave ist ein US-Verarbeiter ohne Personenbezug und wird nur bei Bedarf mit eigenem Abo genutzt.
- Unverändert gilt: Nur URLs, die das Werkzeug in diesem Job geliefert hat, gelten als Quelle. Zusätzlich prüft `HttpSourceChecker` die Erreichbarkeit (HEAD/GET, Status < 400, 5 s, höchstens drei Umleitungen, nur öffentliche IP-Adressen gegen SSRF).

## Datenschutz

- SearXNG läuft auf dem eigenen Server; es gibt **keinen neuen Auftragsverarbeiter**.
- SearXNG fragt Suchmaschinen wie Google, Bing, DuckDuckGo, Startpage und Wikipedia als normaler Client an. Diese sehen die IP-Adresse des Servers und die Suchanfragen. Die Anfragen enthalten nur Ortsnamen, PLZ, Kategorien und Zeitraum aus dem Prompt (versionierte Vorlagen mit Erlaubnisliste der Platzhalter, Snapshot-Test). **Keine** Nutzer-, Moderator- oder Gerätedaten.
- Ohne personenbezogene Daten liegt keine Drittlandübermittlung nach Art. 44 ff. DSGVO vor.
- Mit `WEB_SEARCH_PROVIDER=brave` gilt das Gleiche für Brave (USA). Vor einer produktiven Nutzung den DPA prüfen und den Eintrag im Verarbeiterverzeichnis aktualisieren.
- Einträge: [Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md), [Verarbeitungsverzeichnis Nr. 10](../30-privacy/verarbeitungsverzeichnis.md).

## Konsequenzen

- Keine Kosten und kein Schlüssel. Mehrere Suchmaschinen liefern gute Abdeckung deutscher Seiten, auch lokaler Zeitungen und Gemeindeseiten (Test mit „Stadtfest Aalen 2026“: 28 Treffer).
- **Betriebsrisiko:** Die Suchmaschinen können die Server-IP drosseln oder CAPTCHAs zeigen. Bei unserem Volumen bleibt das voraussichtlich selten: höchstens `AI_SEARCH_MAX_TOOL_CALLS` Anfragen je KI-Suche und `AI_SEARCH_DAILY_LIMIT` Suchen je Moderator und Tag. Fällt die Suche aus, sagt der Job das; dann im Runbook einzelne Engines prüfen oder Brave nutzen.
- **Rechtliches Risiko:** Die automatisierte Abfrage widerspricht den Nutzungsbedingungen einzelner Suchmaschinen (z. B. Google). Bei geringem Volumen und nicht kommerzieller Nutzung nimmt der Projektinhaber das in Kauf. Bei kommerziellem Betrieb ist ein API-Anbieter (Brave oder ein EU-Anbieter) zu wählen.
- Ein zusätzlicher Container im Stack. Das Image ist auf eine Version festgelegt und wird mit den anderen Images aktualisiert, weil sich die Engines der Suchmaschinen ändern.
- Treffer können Social-Media-Beiträge (Facebook, Instagram) sein. Die Quellenprüfung lässt sie zu, wenn sie erreichbar sind; ob sie belastbar sind, entscheiden die Moderierenden beim Prüfen.

## Verworfene Alternativen

- **Brave Search API als Standard:** keine kostenlose Nutzung; bleibt optional.
- **Tavily, Exa, Serper:** kostenlose Kontingente, aber US-Verarbeiter, Schlüssel nötig und Kontingente begrenzt bzw. einmalig.
- **Eingebaute Web-Suche der LLM-Anbieter:** nicht bei allen vier Anbietern vorhanden, die Quellen wären nicht einheitlich prüfbar und der Such-Anbieter nicht getrennt wählbar.
- **Eigenes Crawling:** zu aufwendig, rechtlich (robots.txt, Urheberrecht) und technisch für das Projekt nicht angemessen.
