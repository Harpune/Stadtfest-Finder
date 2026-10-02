import {
  draftErrors,
  emptyForm,
  errorsFromServer,
  EventForm,
  formFromEvent,
  formToPatch,
  ModEventDetail,
  newProgramRow,
  normalizeWebsite,
  publishErrors,
} from './form';

const ACTIVE = new Set(['c1']);

function complete(): EventForm {
  return {
    ...emptyForm(),
    name: 'Herbstfest Wasseralfingen',
    categoryId: 'c1',
    startDate: '2026-10-17',
    endDate: '2026-10-18',
    address: 'Festplatz, 73430 Aalen',
    city: 'Aalen',
    postalCode: '73430',
    lat: 48.86,
    lon: 10.1,
  };
}

describe('publishErrors', () => {
  it('accepts a complete form', () => {
    expect(publishErrors(complete(), ACTIVE)).toEqual({});
  });

  it('marks every missing required field (08-06)', () => {
    expect(publishErrors({...emptyForm(), name: 'Herbstfest'}, ACTIVE)).toEqual(
      {
        categoryId: 'Bitte wähle eine Kategorie.',
        startDate: 'Bitte wähle den Beginn.',
        endDate: 'Bitte wähle das Ende.',
        location: 'Bitte gib eine Adresse ein oder setze einen Pin.',
      },
    );
  });

  it('rejects an end before the start, inactive categories and bad websites', () => {
    const errors = publishErrors(
      {
        ...complete(),
        endDate: '2026-10-16',
        categoryId: 'old',
        websiteUrl: 'not a url',
      },
      ACTIVE,
    );
    expect(errors).toEqual({
      endDate: 'Das Ende liegt vor dem Beginn.',
      categoryId: 'Bitte wähle eine Kategorie.',
      websiteUrl: 'Bitte gib eine gültige Web-Adresse ein.',
    });
  });

  it('drafts only need a name', () => {
    expect(draftErrors({...emptyForm(), name: '  '})).toEqual({
      name: 'Bitte gib einen Namen ein.',
    });
    expect(draftErrors({...emptyForm(), name: 'X'})).toEqual({});
  });
});

describe('conversion', () => {
  it('builds a merge patch with cleared empty texts and complete program rows', () => {
    const form: EventForm = {
      ...complete(),
      openingHours: 'Sa 11–24 Uhr\n\n So 11–19 Uhr ',
      websiteUrl: 'schwaebisch-gmuend.de',
      program: [
        {
          ...newProgramRow('2026-10-17'),
          timeLabel: '11 Uhr',
          title: 'Fassanstich',
        },
        {...newProgramRow(null), title: 'ohne Tag'},
      ],
    };
    const patch = formToPatch(form);
    expect(patch.openingHours).toEqual(['Sa 11–24 Uhr', 'So 11–19 Uhr']);
    expect(patch.websiteUrl).toBe('https://schwaebisch-gmuend.de');
    expect(patch.description).toBeNull();
    expect(patch.program).toEqual([
      {date: '2026-10-17', timeLabel: '11 Uhr', title: 'Fassanstich'},
    ]);
  });

  it('round-trips an event', () => {
    const event: ModEventDetail = {
      id: 'e1',
      regionId: 'r1',
      name: 'Stadtfest',
      shortName: 'Stadtfest',
      status: 'published',
      categoryId: 'c1',
      startDate: '2026-10-03',
      endDate: '2026-10-04',
      openingHours: ['Sa 11–24 Uhr'],
      place: 'Marktplatz',
      address: 'Marktplatz',
      city: 'Schwäbisch Gmünd',
      postalCode: '73525',
      lat: 48.8,
      lon: 9.8,
      program: [{date: '2026-10-03', timeLabel: '11 Uhr', title: 'Eröffnung'}],
      favoriteCount: 86,
      source: 'manual',
      version: 3,
      images: [],
    };
    const form = formFromEvent(event);
    expect(form.openingHours).toBe('Sa 11–24 Uhr');
    expect(formToPatch(form)).toMatchObject({
      name: 'Stadtfest',
      postalCode: '73525',
      program: [{date: '2026-10-03', timeLabel: '11 Uhr', title: 'Eröffnung'}],
    });
  });

  it('keeps explicit URL schemes', () => {
    expect(normalizeWebsite('http://a.de')).toBe('http://a.de');
    expect(normalizeWebsite('  ')).toBe('');
  });
});

describe('errorsFromServer', () => {
  it('maps backend field codes to the form texts', () => {
    expect(
      errorsFromServer({startDate: 'required', endDate: 'before_start'}),
    ).toEqual({
      startDate: 'Bitte wähle den Beginn.',
      endDate: 'Das Ende liegt vor dem Beginn.',
    });
    expect(
      errorsFromServer({location: 'region_mismatch'}, 'region_mismatch'),
    ).toEqual({
      location: 'Der Ort liegt außerhalb deiner Region.',
    });
  });
});
