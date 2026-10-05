/**
 * Event form of the moderation view (R07-US3, US4): form state, conversion from and to the
 * API, and the publication check. The rules mirror `Event.can_publish()` in the backend so
 * the app can mark fields before sending; the backend checks again (422).
 */
import type {components} from '@/api/generated/schema';
import {strings} from '@/strings/de';

export type ModEventDetail = components['schemas']['ModEventDetail'];
export type ModEventPatch = components['schemas']['ModEventPatch'];
export type ModEventCreate = components['schemas']['ModEventCreate'];

export type LocationMode = 'address' | 'pin';

export interface ProgramRow {
  /** Stable key for list rendering. */
  key: string;
  date: string | null;
  timeLabel: string;
  title: string;
}

export interface EventForm {
  name: string;
  categoryId: string | null;
  startDate: string | null;
  endDate: string | null;
  /** One line per opening hours entry. */
  openingHours: string;
  locationMode: LocationMode;
  /** Address as shown in the field, e.g. "Marktplatz, 73525 Schwäbisch Gmünd". */
  address: string;
  place: string;
  city: string;
  postalCode: string | null;
  lat: number | null;
  lon: number | null;
  description: string;
  program: ProgramRow[];
  price: string;
  transit: string;
  parking: string;
  websiteUrl: string;
}

export type FormField =
  'name' | 'categoryId' | 'startDate' | 'endDate' | 'location' | 'websiteUrl';

export type FormErrors = Partial<Record<FormField, string>>;

let rowCounter = 0;

export function newProgramRow(date: string | null = null): ProgramRow {
  rowCounter += 1;
  return {key: `row-${rowCounter}`, date, timeLabel: '', title: ''};
}

export function emptyForm(): EventForm {
  return {
    name: '',
    categoryId: null,
    startDate: null,
    endDate: null,
    openingHours: '',
    locationMode: 'address',
    address: '',
    place: '',
    city: '',
    postalCode: null,
    lat: null,
    lon: null,
    description: '',
    program: [],
    price: '',
    transit: '',
    parking: '',
    websiteUrl: '',
  };
}

export function formFromEvent(event: ModEventDetail): EventForm {
  return {
    name: event.name,
    categoryId: event.categoryId ?? null,
    startDate: event.startDate ?? null,
    endDate: event.endDate ?? null,
    openingHours: event.openingHours.join('\n'),
    locationMode: 'address',
    address: event.address,
    place: event.place,
    city: event.city,
    postalCode: event.postalCode ?? null,
    lat: event.lat ?? null,
    lon: event.lon ?? null,
    description: event.description ?? '',
    program: event.program.map(item => ({
      ...newProgramRow(item.date),
      timeLabel: item.timeLabel,
      title: item.title,
    })),
    price: event.price ?? '',
    transit: event.transit ?? '',
    parking: event.parking ?? '',
    websiteUrl: event.websiteUrl ?? '',
  };
}

const orNull = (value: string): string | null => value.trim() || null;

/** All editable fields as a full merge patch; empty texts are cleared (`null`). */
export function formToPatch(form: EventForm): ModEventPatch {
  return {
    name: form.name.trim(),
    categoryId: form.categoryId,
    startDate: form.startDate,
    endDate: form.endDate,
    openingHours: form.openingHours
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean),
    place: form.place.trim() || null,
    address: form.address.trim() || null,
    city: form.city.trim() || null,
    postalCode: form.postalCode,
    lat: form.lat,
    lon: form.lon,
    description: orNull(form.description),
    program: form.program
      .filter(row => row.date && row.title.trim())
      .map(row => ({
        date: row.date as string,
        timeLabel: row.timeLabel.trim(),
        title: row.title.trim(),
      })),
    price: orNull(form.price),
    transit: orNull(form.transit),
    parking: orNull(form.parking),
    websiteUrl: orNull(normalizeWebsite(form.websiteUrl)),
  };
}

export function formToCreate(form: EventForm): ModEventCreate {
  const {name, ...rest} = formToPatch(form);
  return {name: name ?? '', ...rest};
}

/** "schwaebisch-gmuend.de" → "https://schwaebisch-gmuend.de" (as shown in the design). */
export function normalizeWebsite(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '';
  return /^[a-z][a-z0-9+.-]*:/i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function isWebUrl(value: string): boolean {
  return /^https?:\/\/[^\s/]+\.[^\s]+$/i.test(value);
}

/** Only the name is required for a draft. */
export function draftErrors(form: EventForm): FormErrors {
  return form.name.trim() ? {} : {name: strings.mod.errors.name};
}

/** Required fields for publishing (R07-US4); empty if the form may be published. */
export function publishErrors(
  form: EventForm,
  activeCategoryIds: ReadonlySet<string>,
): FormErrors {
  const errors: FormErrors = {...draftErrors(form)};
  if (!form.categoryId || !activeCategoryIds.has(form.categoryId)) {
    errors.categoryId = strings.mod.errors.category;
  }
  if (!form.startDate) errors.startDate = strings.mod.errors.start;
  if (!form.endDate) errors.endDate = strings.mod.errors.end;
  else if (form.startDate && form.endDate < form.startDate) {
    errors.endDate = strings.mod.errors.endBeforeStart;
  }
  if (form.lat === null || form.lon === null) {
    errors.location = strings.mod.errors.location;
  }
  const website = normalizeWebsite(form.websiteUrl);
  if (website && !isWebUrl(website))
    errors.websiteUrl = strings.mod.errors.website;
  return errors;
}

/** Maps backend field codes (`422 validation_failed`) to the same texts. */
export function errorsFromServer(
  fields: Record<string, string> | undefined,
): FormErrors {
  const errors: FormErrors = {};
  for (const [field, problem] of Object.entries(fields ?? {})) {
    switch (field) {
      case 'name':
        errors.name = strings.mod.errors.name;
        break;
      case 'categoryId':
        errors.categoryId = strings.mod.errors.category;
        break;
      case 'startDate':
        errors.startDate = strings.mod.errors.start;
        break;
      case 'endDate':
        errors.endDate =
          problem === 'before_start'
            ? strings.mod.errors.endBeforeStart
            : strings.mod.errors.end;
        break;
      case 'location':
        errors.location = strings.mod.errors.location;
        break;
      case 'websiteUrl':
        errors.websiteUrl = strings.mod.errors.website;
        break;
    }
  }
  return errors;
}
