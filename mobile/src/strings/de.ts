/**
 * All user-facing German texts. Wording comes verbatim from the design/prototype
 * (00-docs/15-design). Do not scatter strings across components.
 */
export const strings = {
  app: {
    name: 'Stadtfest-Finder',
    tagline:
      'Stadtfeste, Volksfeste, Kirmes und Weihnachtsmärkte in deiner Nähe.',
    comingSoon: 'Die Karte folgt in Kürze.',
  },
  common: {
    loading: 'Einen Moment …',
    retry: 'Erneut versuchen',
    close: 'Schließen',
  },
  discover: {
    searchPlaceholder: 'Fest oder Ort suchen',
    clearSearch: 'Suche leeren',
    openFilter: 'Filter öffnen',
    activeFilters: (n: number) => `${n} aktive Filter`,
    profile: 'Profil',
    profileSoon: 'Anmeldung und Profil folgen in Kürze.',
    detailSoon: 'Die Detailseite folgt in Kürze.',
    favoriteSoon: 'Favoriten folgen in Kürze.',
    loadingEvents: 'Feste werden geladen …',
    loadFailed: 'Feste konnten nicht geladen werden',
    offline: (time: string) => `Offline · zuletzt geladen um ${time}`,
    zoomIn: 'Zoome hinein, um alle Feste zu sehen',
    attribution: '© MapTiler © OpenStreetMap-Mitwirkende',
    map: 'Karte',
    list: 'Liste',
    listHeader: (n: number, km: number) =>
      `${n} ${n === 1 ? 'Fest' : 'Feste'} · bis ${km} km`,
    sortedByDate: 'nach Datum',
    runningNow: 'Läuft gerade',
    photo: 'Foto',
    eventPhoto: 'Festfoto',
    distance: (km: number) =>
      `${km.toLocaleString('de-DE', {maximumFractionDigits: km < 10 ? 1 : 0})} km`,
    zoomInButton: 'Hineinzoomen',
    zoomOutButton: 'Herauszoomen',
    locate: 'Auf meinen Standort zentrieren',
    cluster: (n: number) => `${n} Feste, zum Vergrößern tippen`,
    emptyTitle: 'Keine Feste im Umkreis',
    emptyText: (km: number) =>
      `Im Umkreis von ${km} km gibt es mit diesen Filtern gerade nichts. Erweitere den Umkreis oder setze die Filter zurück.`,
    expandRadius: 'Umkreis auf 300 km',
    resetFilters: 'Filter zurücksetzen',
    noResultsTitle: (q: string) => `Kein Fest für „${q}“`,
    noResultsText: 'Prüfe die Schreibweise oder suche nach einer Stadt.',
  },
  filter: {
    title: 'Filter',
    time: 'Zeitraum',
    timeAll: 'Alle Termine',
    timeToday: 'Heute',
    timeWeekend: 'Dieses Wochenende',
    timeMonths: 'Zeitraum wählen',
    monthsHint: 'Monate wählen (mehrere möglich)',
    monthsChip: (n: number) => (n === 1 ? '1 Monat' : `${n} Monate`),
    category: 'Kategorie',
    distance: 'Entfernung',
    upTo: (km: number) => `bis ${km} km`,
    fromLocation: (place: string) => `vom Standort ${place}`,
    fromLocationUnknown: 'vom Standort',
    fromMapCenter: 'vom Kartenmittelpunkt',
    reset: 'Zurücksetzen',
    apply: (n: number) => `${n} ${n === 1 ? 'Fest' : 'Feste'} anzeigen`,
    applyEmpty: 'Keine Treffer – trotzdem anwenden',
    km: (km: number) => `${km} km`,
  },
} as const;
