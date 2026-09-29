import {DEFAULT_FILTER} from './filter';
import {discoverReducer, INITIAL_DISCOVER_STATE as S} from './state';

describe('discoverReducer', () => {
  it('keeps search, filter and selection when switching views', () => {
    const before = {
      ...S,
      query: 'Aalen',
      selectedEventId: 'e1',
      filter: {...DEFAULT_FILTER, categoryIds: ['c1']},
    };
    const after = discoverReducer(before, {type: 'setView', view: 'list'});
    expect(after).toEqual({...before, view: 'list'});
  });

  it('toggles categories (multi-select)', () => {
    let state = discoverReducer(S, {type: 'toggleCategory', categoryId: 'a'});
    state = discoverReducer(state, {type: 'toggleCategory', categoryId: 'b'});
    expect(state.filter.categoryIds).toEqual(['a', 'b']);
    state = discoverReducer(state, {type: 'toggleCategory', categoryId: 'a'});
    expect(state.filter.categoryIds).toEqual(['b']);
  });

  it('expands the radius to 300 km', () => {
    expect(discoverReducer(S, {type: 'expandRadius'}).filter.radiusKm).toBe(
      300,
    );
  });

  it('resets filter and search, but keeps the view', () => {
    const state = discoverReducer(
      {
        ...S,
        view: 'list',
        query: 'xyz',
        filter: {...DEFAULT_FILTER, radiusKm: 10},
      },
      {type: 'resetAll'},
    );
    expect(state).toEqual({...S, view: 'list'});
  });

  it('prunes unknown categories and keeps identity when nothing changes', () => {
    const withCats = {
      ...S,
      filter: {...DEFAULT_FILTER, categoryIds: ['a', 'gone']},
    };
    expect(
      discoverReducer(withCats, {
        type: 'pruneCategories',
        activeCategoryIds: ['a'],
      }).filter.categoryIds,
    ).toEqual(['a']);
    expect(
      discoverReducer(S, {type: 'pruneCategories', activeCategoryIds: []}),
    ).toBe(S);
  });
});
