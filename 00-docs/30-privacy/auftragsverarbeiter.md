# Auftragsverarbeiter und externe Dienste

> Stand R10. Jeder neue Dienst mit Zugriff auf personenbezogene Daten braucht einen Eintrag und ggf. ein ADR (Nicht-EU).

| Dienst | Zweck | Standort | Personenbezogene Daten | Abschaltbar per ENV | ADR | Status |
|---|---|---|---|---|---|---|
| Zitadel Cloud | Anmeldung, Rollen, Kontolöschung per Management-API | EU-Region | Konto (E-Mail, Name, Anmeldedaten, Rollen, Region) | nein (Kern) | 0003, 0010 | AV-Vertrag vor Produktivstart (R16) |
| Eigener Server (Heimserver) | Hosting API, Worker, DB, Redis, Objektspeicher, Nominatim | EU (Deutschland) | alle Backend-Daten, Festbilder | – | 0002, 0006, 0007, 0011 | geplant (R16) |
| GitHub (Actions, GHCR) | CI, Container-Registry | USA | keine Nutzerdaten (nur Code, synthetische Testdaten) | – | – | aktiv |
| Mistral AI (Standard) / Ollama (selbst gehostet) | Sprachmodell der KI-Suche | Mistral: EU (Frankreich); Ollama: eigener Server | **keine** (nur PLZ, Ortsname, Radius, Zeitraum, Kategorien, öffentliche Suchtreffer) | ja (`LLM_PROVIDER`) | 0012 | aktiv ab R10, DPA vor Produktivstart |
| OpenAI / Anthropic (optional) | Sprachmodell der KI-Suche | USA | keine (wie oben) | ja (`LLM_PROVIDER=mistral` oder `ollama`) | 0012, 0014 | optional, DPA vor produktivem Einsatz |
| Eigener Server: SearXNG (Standard) | Web-Suche als Tool der KI-Suche; fragt Suchmaschinen (Google, Bing, DuckDuckGo …) als Client an | EU (Deutschland); die Suchmaschinen sehen Server-IP und Suchanfragen | keine (nur Suchanfragen aus Ortsname, PLZ, Kategorien, Zeitraum) | ja (`WEB_SEARCH_PROVIDER`; in Produktion KI-Suche per `AI_SEARCH_DAILY_LIMIT=0` stoppen) | 0013 | aktiv ab R10, kein Auftragsverarbeiter |
| Brave Search API (Brave Software, Inc.), optional | Web-Suche, Alternative zu SearXNG | USA | keine (wie oben) | ja (`WEB_SEARCH_PROVIDER=searxng`) | 0013 | optional, DPA vor produktivem Einsatz |
| MapTiler Cloud (MapTiler AG) | Kartenkacheln und -stile (Abruf direkt aus der App) | Schweiz (Angemessenheitsbeschluss); Hosting-Standorte im DPA prüfen | IP-Adresse, abgerufene Kacheln (≈ betrachteter Kartenausschnitt) | ja (`EXPO_PUBLIC_MAPTILER_KEY` leer → Offline-Stil ohne Abruf) | 0009 | aktiv ab R03, DPA vor Produktivstart |
| Expo Push / APNs / FCM | Push-Benachrichtigungen | USA | Push-Token, generische Texte, IDs | ja (`PUSH_PROVIDER`) | folgt R11 | geplant |
