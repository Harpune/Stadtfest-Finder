import {displayHost, eventShareUrl, mapsRouteUrl, safeWebUrl} from './links';

describe('safeWebUrl', () => {
  it.each([
    'https://oktoberfest.de',
    'http://www.aalen.de/stadtfest?jahr=2026#programm',
    'https://example.org:8443/pfad',
  ])('accepts %s', url => {
    expect(safeWebUrl(url)).toBe(url);
  });

  it.each([
    'javascript:alert(1)',
    'file:///etc/passwd',
    'intent://evil#Intent;end',
    'stadtfest://f/123',
    'ftp://example.org',
    'https://localhost',
    'https://user@evil.org',
    'https://exa mple.org',
    'oktoberfest.de',
    '',
    null,
    undefined,
  ])('rejects %s', url => {
    expect(safeWebUrl(url)).toBeNull();
  });
});

describe('mapsRouteUrl', () => {
  const target = {lat: 48.8368, lon: 10.0932, name: 'Reichsstädter Tage'};

  it('opens Apple Maps with destination and name on iOS', () => {
    expect(mapsRouteUrl('ios', target)).toBe(
      'https://maps.apple.com/?daddr=48.8368,10.0932&q=Reichsst%C3%A4dter%20Tage',
    );
  });

  it('uses a geo: intent with a labelled pin on Android', () => {
    expect(mapsRouteUrl('android', target)).toBe(
      'geo:48.8368,10.0932?q=48.8368,10.0932(Reichsst%C3%A4dter%20Tage)',
    );
  });
});

describe('links', () => {
  it('builds the share URL on the app link domain', () => {
    expect(eventShareUrl('24b84e9c-31ad')).toBe(
      'https://stadtfest.herderstreet.de/f/24b84e9c-31ad',
    );
  });

  it('shows a short host', () => {
    expect(displayHost('https://www.oktoberfest.de/de/programm')).toBe(
      'oktoberfest.de',
    );
  });
});
