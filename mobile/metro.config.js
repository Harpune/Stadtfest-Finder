// Metro configuration. Storybook is bundled only when STORYBOOK_ENABLED=true.
const {getDefaultConfig} = require('expo/metro-config');
const {withStorybook} = require('@storybook/react-native/metro/withStorybook');

const config = getDefaultConfig(__dirname);

module.exports = withStorybook(config, {
  enabled: process.env.STORYBOOK_ENABLED === 'true',
  configPath: './.rnstorybook',
});
