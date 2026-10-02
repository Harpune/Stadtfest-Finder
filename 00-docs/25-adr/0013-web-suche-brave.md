# 0013 · Web-Suche über die Brave Search API

- **Status:** angenommen
- **Datum:** 2026-10-02

## Kontext

Das Sprachmodell der KI-Suche (ADR 0012) braucht ein Werkzeug, um aktuelle Veranstaltungsseiten zu finden. Jeder Fund muss eine Quelle aus diesen Suchergebnissen tragen. Der Such-Anbieter soll unabhängig vom LLM-Anbieter sein und per ENV austauschbar. EU-Anbieter werden bevorzugt (CLAUDE.md „Privacy“).

## Entscheidung

- Die **Brave Search API** (Brave Software, Inc., USA) implementiert den Port `WebSearchPort` (`adapters/outbound/search/brave.py`).
- Auswahl per ENV: `WEB_SEARCH_PROVIDER=brave|fake`, Schlüssel in `WEB_SEARCH_API_KEY`. `fake` (feste Treffer) ist nur in `dev` und `test` erlaubt.
- Anfrage: `GET https://api.search.brave.com/res/v1/web/search` mit `q`, `count` (höchstens 20), `country=DE`, `search_lang=de`, `safesearch=strict`. Der Adapter gibt nur URL, Titel und Snippet an das Modell weiter.
- Nur URLs, die das Werkzeug in diesem Job geliefert hat, gelten als Quelle. Zusätzlich prüft `HttpSourceChecker` die Erreichbarkeit (HEAD/GET, Status < 400, 5 s, höchstens drei Umleitungen, nur öffentliche IP-Adressen gegen SSRF).
- Fällt die Suche aus, endet der Job mit `search_unavailable`. Es gibt keinen stillen Rückfall auf einen anderen Anbieter.

## Datenschutz

- Brave ist ein **Auftragsverarbeiter in den USA**. Übertragen werden nur die Suchanfragen, die das Modell bildet: Ortsname, PLZ, Kategorien, Zeitraum, z. B. „Feste Ostalb Herbst“. Die Anfragen stammen aus dem Prompt, der nur diese Felder enthält (reine Funktion `build_prompt`, Snapshot-Test). **Keine** Nutzer-, Moderator- oder Gerätedaten, keine IP-Adressen von Nutzern (der Server ruft die API auf).
- Rechtsgrundlage für die Übermittlung: Es fließen keine personenbezogenen Daten, Art. 44 ff. DSGVO greifen deshalb nicht. Vorsorglich vor dem Produktivstart: AV-Vertrag bzw. Data Processing Addendum von Brave prüfen und die Zertifizierung nach dem EU-U.S. Data Privacy Framework im Verarbeiterverzeichnis nachtragen.
- Abschaltbar: `WEB_SEARCH_PROVIDER=fake` außerhalb der Produktion. In Produktion schaltet man die KI-Suche ab, indem man Moderatoren den Start nicht anbietet (`AI_SEARCH_DAILY_LIMIT=0`).
- Einträge: [Auftragsverarbeiter](../30-privacy/auftragsverarbeiter.md), [Verarbeitungsverzeichnis Nr. 10](../30-privacy/verarbeitungsverzeichnis.md).

## Konsequenzen

- Eigener Index statt Bing- oder Google-Wiederverkauf, gute Abdeckung deutscher Seiten, einfache Abrechnung pro Anfrage. Kosten und Limits hängen vom gewählten Tarif ab (siehe [Runbook](../40-operations/web-suche.md)).
- Ein Wechsel (z. B. zu einem EU-Anbieter) braucht nur einen weiteren Adapter für `WebSearchPort` und einen ENV-Wert. Use Cases und Prompt bleiben gleich.

## Verworfene Alternativen

- **Eingebaute Web-Suche der LLM-Anbieter:** nicht bei allen vier Anbietern vorhanden, die Quellen wären nicht einheitlich prüfbar und der Such-Anbieter nicht getrennt wählbar.
- **Google Programmable Search / Bing:** Die Bing Search API ist eingestellt. Google Programmable Search hat enge Kontingente und schränkt die Suche über das gesamte Web ein.
- **EU-Anbieter (z. B. Qwant, Ecosia):** zum Entscheidungszeitpunkt keine allgemein zugängliche, dokumentierte Such-API. Bleibt die bevorzugte Option, sobald es eine gibt.
- **Eigenes Crawling:** zu aufwendig, rechtlich (robots.txt, Urheberrecht) und technisch für das Projekt nicht angemessen.
