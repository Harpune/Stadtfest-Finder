# Auftragsverarbeiter und externe Dienste

> Stand R01. Jeder neue Dienst mit Zugriff auf personenbezogene Daten braucht einen Eintrag und ggf. ein ADR (Nicht-EU).

| Dienst | Zweck | Standort | Personenbezogene Daten | Abschaltbar per ENV | ADR | Status |
|---|---|---|---|---|---|---|
| Zitadel Cloud | Anmeldung, Rollen | EU-Region | Konto (E-Mail, Name, Anmeldedaten) | nein (Kern) | 0003 | geplant (R05/R16) |
| Eigener Server (Heimserver) | Hosting API, Worker, DB, Redis, Objektspeicher, Nominatim | EU (Deutschland) | alle Backend-Daten | – | 0002, 0006, 0007 | geplant (R16) |
| GitHub (Actions, GHCR) | CI, Container-Registry | USA | keine Nutzerdaten (nur Code, synthetische Testdaten) | – | – | aktiv |
| KI-Anbieter (Mistral/OpenAI/Anthropic/Ollama) | KI-Suche | je Anbieter | **keine** (nur PLZ, Radius, Zeitraum, Kategorien) | ja (`LLM_PROVIDER`) | folgt R10 | geplant |
| Web-Such-API | Tool der KI-Suche | je Anbieter | keine | ja | folgt R10 | geplant |
| MapTiler Cloud (MapTiler AG) | Kartenkacheln und -stile (Abruf direkt aus der App) | Schweiz (Angemessenheitsbeschluss); Hosting-Standorte im DPA prüfen | IP-Adresse, abgerufene Kacheln (≈ betrachteter Kartenausschnitt) | ja (`EXPO_PUBLIC_MAPTILER_KEY` leer → Offline-Stil ohne Abruf) | 0009 | aktiv ab R03, DPA vor Produktivstart |
| Expo Push / APNs / FCM | Push-Benachrichtigungen | USA | Push-Token, generische Texte, IDs | ja (`PUSH_PROVIDER`) | folgt R11 | geplant |
