import {formatAddress} from './EventDetailScreen';

describe('formatAddress', () => {
  it('joins place, street and locality', () => {
    expect(
      formatAddress({
        place: 'Festplatz',
        address: 'Karlstraße 26',
        postalCode: '73433',
        city: 'Aalen',
      }),
    ).toBe('Festplatz, Karlstraße 26, 73433 Aalen');
  });

  it('drops parts that another part already contains', () => {
    expect(
      formatAddress({
        place: 'Marktplatz 1',
        address: 'Marktplatz 1, 73430 Aalen',
        postalCode: '73430',
        city: 'Aalen',
      }),
    ).toBe('Marktplatz 1, 73430 Aalen');
    expect(
      formatAddress({
        place: '',
        address: 'Aalen',
        postalCode: '73430',
        city: 'Aalen',
      }),
    ).toBe('73430 Aalen');
  });

  it('shows coordinates of a pin without street and skips empty parts', () => {
    expect(
      formatAddress({
        place: '',
        address: '48.86038, 10.09923',
        postalCode: '',
        city: '',
      }),
    ).toBe('48.86038, 10.09923');
  });
});
