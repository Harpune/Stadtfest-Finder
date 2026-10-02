import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {useAuth} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import {CategoriesScreen} from './CategoriesScreen';
import {CategoryFormScreen} from './CategoryFormScreen';
import type {ModCategory} from './useModCategories';

jest.mock('@/features/auth/AuthProvider', () => ({useAuth: jest.fn()}));

const STADTFEST: ModCategory = {
  id: 'c1',
  name: 'Stadtfest',
  emoji: '🎪',
  color: '#FFB547',
  active: true,
  sortOrder: 0,
  eventCount: 3,
};
const VOLKSFEST: ModCategory = {
  id: 'c2',
  name: 'Volksfest & Kirmes',
  emoji: '🎡',
  color: '#FF6B8B',
  active: true,
  sortOrder: 1,
  eventCount: 0,
};
const WEIN: ModCategory = {
  id: 'c3',
  name: 'Weinfest',
  emoji: '🍷',
  color: '#C792EA',
  active: false,
  sortOrder: 2,
  eventCount: 0,
};

interface Call {
  method: string;
  path: string;
  query: string;
  body: string;
}

type Handler = (call: Call) => {status: number; body?: unknown} | undefined;

function mockApi(handler: Handler = () => undefined): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const url = new URL(request.url);
    const call = {
      method: request.method,
      path: url.pathname,
      query: url.search,
      body: request.method === 'GET' ? '' : await request.text(),
    };
    calls.push(call);
    const json = (body: unknown, status = 200) =>
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: {'Content-Type': 'application/json'},
      });
    const custom = handler(call);
    if (custom) return json(custom.body, custom.status);
    if (call.path === '/v1/mod/categories' && call.method === 'GET') {
      return json([STADTFEST, VOLKSFEST, WEIN]);
    }
    return json({error: 'not_found', message: ''}, 404);
  });
  return calls;
}

function asAdmin(admin: boolean) {
  jest.mocked(useAuth).mockReturnValue({
    isCategoryAdmin: admin,
    isModerator: true,
  } as ReturnType<typeof useAuth>);
}

async function render(ui: React.ReactElement) {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe('CategoriesScreen (10-01)', () => {
  afterEach(() => jest.restoreAllMocks());

  it('shows the chip preview, counts and deactivated categories', async () => {
    asAdmin(true);
    mockApi();
    await render(<CategoriesScreen />);

    expect(await screen.findByText('3 Feste')).toBeOnTheScreen();
    expect(screen.getByText('Deaktiviert · 0 Feste')).toBeOnTheScreen();
    expect(screen.getByTestId('mod.categories.preview.c1')).toBeOnTheScreen();
    expect(
      screen.queryByTestId('mod.categories.preview.c3'),
    ).not.toBeOnTheScreen();
    expect(screen.getByTestId('mod.categories.new')).toBeOnTheScreen();
    expect(
      screen.getByTestId('mod.categories.list.row.0.handle'),
    ).toBeOnTheScreen();
  });

  it('moves a category with the accessibility action and saves the order', async () => {
    asAdmin(true);
    const calls = mockApi(call =>
      call.path === '/v1/mod/categories/order'
        ? {status: 200, body: [VOLKSFEST, STADTFEST, WEIN]}
        : undefined,
    );
    await render(<CategoriesScreen />);
    const handle = await screen.findByTestId(
      'mod.categories.list.row.0.handle',
    );

    await fireEvent(handle, 'accessibilityAction', {
      nativeEvent: {actionName: 'increment'},
    });

    expect(
      await screen.findByText(
        'Reihenfolge gespeichert · Chips auf der Startseite aktualisiert',
      ),
    ).toBeOnTheScreen();
    const order = calls.find(c => c.path === '/v1/mod/categories/order');
    expect(JSON.parse(order?.body ?? '{}')).toEqual({ids: ['c2', 'c1', 'c3']});
  });

  it('is read-only without category_admin', async () => {
    asAdmin(false);
    mockApi();
    await render(<CategoriesScreen />);

    expect(await screen.findByText('3 Feste')).toBeOnTheScreen();
    expect(screen.queryByTestId('mod.categories.new')).not.toBeOnTheScreen();
    expect(
      screen.queryByTestId('mod.categories.list.row.0.handle'),
    ).not.toBeOnTheScreen();
  });
});

describe('CategoryFormScreen (10-02 to 10-04)', () => {
  beforeEach(() => jest.mocked(router.back).mockClear());
  afterEach(() => jest.restoreAllMocks());

  it('updates the preview live and creates the category', async () => {
    asAdmin(true);
    const calls = mockApi(call =>
      call.method === 'POST'
        ? {status: 201, body: {...WEIN, id: 'new', name: 'Herbstmarkt'}}
        : undefined,
    );
    await render(<CategoryFormScreen categoryId={null} />);

    await fireEvent.changeText(
      screen.getByTestId('mod.category.name'),
      'Herbstmarkt',
    );
    await fireEvent.press(screen.getByTestId('mod.category.emoji.9'));
    await fireEvent.press(screen.getByTestId('mod.category.color.4'));
    expect(screen.getAllByText('Herbstmarkt').length).toBeGreaterThan(0);
    expect(screen.getAllByText('🎃').length).toBeGreaterThan(1);

    await fireEvent.press(screen.getByTestId('mod.category.save'));

    expect(await screen.findByText('Kategorie angelegt')).toBeOnTheScreen();
    const create = calls.find(c => c.method === 'POST');
    expect(JSON.parse(create?.body ?? '{}')).toEqual({
      name: 'Herbstmarkt',
      emoji: '🎃',
      color: '#7ED957',
      active: true,
    });
    expect(router.back).toHaveBeenCalled();
  });

  it('shows the server error for a duplicate name', async () => {
    asAdmin(true);
    mockApi(call =>
      call.method === 'PATCH'
        ? {
            status: 422,
            body: {
              error: 'validation_failed',
              message: '',
              fields: {name: 'duplicate'},
            },
          }
        : undefined,
    );
    await render(<CategoryFormScreen categoryId="c2" />);
    await fireEvent.changeText(
      await screen.findByTestId('mod.category.name'),
      'Stadtfest',
    );
    await fireEvent.press(screen.getByTestId('mod.category.save'));

    expect(
      await screen.findByText('Diesen Namen gibt es schon.'),
    ).toBeOnTheScreen();
  });

  it('requires a replacement before deleting a category with events', async () => {
    asAdmin(true);
    const calls = mockApi(call =>
      call.method === 'DELETE'
        ? {status: 200, body: {movedEvents: 3, replacementId: 'c2'}}
        : undefined,
    );
    await render(<CategoryFormScreen categoryId="c1" />);
    await fireEvent.press(await screen.findByTestId('mod.category.delete'));

    expect(
      screen.getByText(/3 Feste sind dieser Kategorie zugeordnet/),
    ).toBeOnTheScreen();
    expect(screen.getByText('Ersatz wählen')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('mod.category.replacement.c2'));
    await fireEvent.press(screen.getByText('Löschen und verschieben'));

    expect(
      await screen.findByText(
        'Gelöscht · 3 Feste nach „Volksfest & Kirmes“ verschoben',
      ),
    ).toBeOnTheScreen();
    const remove = calls.find(c => c.method === 'DELETE');
    expect(remove?.query).toBe('?replacementId=c2');
  });

  it('deletes a category without events after a simple confirmation', async () => {
    asAdmin(true);
    const calls = mockApi(call =>
      call.method === 'DELETE'
        ? {status: 200, body: {movedEvents: 0, replacementId: null}}
        : undefined,
    );
    await render(<CategoryFormScreen categoryId="c3" />);
    await fireEvent.press(await screen.findByTestId('mod.category.delete'));
    await fireEvent.press(screen.getByText('Endgültig löschen'));

    await waitFor(() =>
      expect(calls.some(c => c.method === 'DELETE')).toBe(true),
    );
    expect(await screen.findByText('Kategorie gelöscht')).toBeOnTheScreen();
  });

  it('is read-only without category_admin', async () => {
    asAdmin(false);
    mockApi();
    await render(<CategoryFormScreen categoryId="c1" />);

    expect(
      await screen.findByText('Nur Kategorie-Admins können Kategorien ändern.'),
    ).toBeOnTheScreen();
    expect(screen.queryByTestId('mod.category.save')).not.toBeOnTheScreen();
    expect(screen.queryByTestId('mod.category.delete')).not.toBeOnTheScreen();
  });
});
