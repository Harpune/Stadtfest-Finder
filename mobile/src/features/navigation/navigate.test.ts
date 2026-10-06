import {router} from 'expo-router';

import {navigate, PUSH_LOCK_MS, resetNavigationLock} from './navigate';

jest.mock('expo-router', () => ({router: {push: jest.fn()}}));

describe('navigate', () => {
  beforeEach(() => {
    resetNavigationLock();
    jest.mocked(router.push).mockClear();
  });

  it('ignores fast repeated taps', () => {
    expect(navigate('/f/e1', 1000)).toBe(true);
    expect(navigate('/f/e1', 1100)).toBe(false);
    expect(navigate('/f/e2', 1000 + PUSH_LOCK_MS - 1)).toBe(false);
    expect(router.push).toHaveBeenCalledTimes(1);
  });

  it('opens again after the lock', () => {
    navigate('/f/e1', 1000);
    expect(navigate('/f/e1', 1000 + PUSH_LOCK_MS)).toBe(true);
    expect(router.push).toHaveBeenCalledTimes(2);
  });
});
