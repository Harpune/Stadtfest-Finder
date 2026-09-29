/**
 * Discover screen state (R03, state proposal of the design reference): view, search text,
 * applied filter and the selected event. Map and list share it, so switching views keeps
 * search, filter and selection without reloading.
 */
import {
  DEFAULT_FILTER,
  DiscoverFilter,
  pruneCategories,
  toggleValue,
} from './filter';

export type DiscoverView = 'map' | 'list';

export interface DiscoverState {
  view: DiscoverView;
  query: string;
  filter: DiscoverFilter;
  selectedEventId: string | null;
}

export const INITIAL_DISCOVER_STATE: DiscoverState = {
  view: 'map',
  query: '',
  filter: DEFAULT_FILTER,
  selectedEventId: null,
};

export type DiscoverAction =
  | {type: 'setView'; view: DiscoverView}
  | {type: 'setQuery'; query: string}
  | {type: 'applyFilter'; filter: DiscoverFilter}
  | {type: 'toggleCategory'; categoryId: string}
  | {type: 'resetAll'}
  | {type: 'select'; eventId: string | null}
  | {type: 'pruneCategories'; activeCategoryIds: readonly string[]};

export function discoverReducer(
  state: DiscoverState,
  action: DiscoverAction,
): DiscoverState {
  switch (action.type) {
    case 'setView':
      return state.view === action.view ? state : {...state, view: action.view};
    case 'setQuery':
      return {...state, query: action.query};
    case 'applyFilter':
      return {...state, filter: action.filter};
    case 'toggleCategory':
      return {
        ...state,
        filter: {
          ...state.filter,
          categoryIds: toggleValue(state.filter.categoryIds, action.categoryId),
        },
      };
    case 'resetAll':
      // "Filter zurücksetzen" in the empty state resets filters AND search (R03-US8).
      return {...state, filter: DEFAULT_FILTER, query: ''};
    case 'select':
      return {...state, selectedEventId: action.eventId};
    case 'pruneCategories': {
      const filter = pruneCategories(state.filter, action.activeCategoryIds);
      return filter === state.filter ? state : {...state, filter};
    }
  }
}
