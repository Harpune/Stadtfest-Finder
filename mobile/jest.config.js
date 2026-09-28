/** Jest configuration for components and features (Jest + RN Testing Library). */
module.exports = {
  preset: 'jest-expo',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {'^@/(.*)$': '<rootDir>/src/$1'},
  testPathIgnorePatterns: ['/node_modules/', '/.maestro/'],
};
