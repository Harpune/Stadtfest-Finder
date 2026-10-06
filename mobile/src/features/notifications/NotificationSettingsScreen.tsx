/**
 * Notification settings (07-02, 07-03, R11-US2): one switch per type, reminder time, home
 * by city or ZIP code (or the current location, resolved on the server and then
 * discarded), radius with a preview, and "Konto löschen".
 */
import * as Location from 'expo-location';
import {router} from 'expo-router';
import React, {useEffect, useState} from 'react';
import {
  ActivityIndicator,
  Linking,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {$api, fetchClient} from '@/api/client';
import {
  Button,
  Chip,
  Icon,
  IconButton,
  LinkRow,
  PlaceSuggestion,
  RangeSlider,
  SectionHeader,
  SwitchRow,
  Text,
  TextField,
  useToast,
} from '@/components';
import {useConfirmDeleteAccount} from '@/features/account/useConfirmDeleteAccount';
import {useDebouncedValue} from '@/features/discover/useDebouncedValue';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {canAskForPermission, isPermissionGranted} from './push';
import {usePush} from './PushProvider';
import {
  NotificationSettings,
  useNotificationSettings,
} from './useNotificationSettings';

const s = strings.notificationSettings;
type Toggle = 'remind' | 'near' | 'change' | 'invite' | 'rsvp';
const TOGGLES: Toggle[] = ['remind', 'near', 'change', 'invite', 'rsvp'];

export function NotificationSettingsScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const {settings, query, change} = useNotificationSettings();
  const deletion = useConfirmDeleteAccount();

  let body: React.ReactNode;
  if (settings) {
    body = <SettingsForm settings={settings} change={change} />;
  } else if (query.isError) {
    body = (
      <View style={styles.gap}>
        <Text variant="body" tone="muted">
          {s.loadFailed}
        </Text>
        <Button
          label={strings.notifications.retry}
          variant="secondary"
          onPress={() => void query.refetch()}
          testID="settings.retry"
        />
      </View>
    );
  } else {
    body = <ActivityIndicator testID="settings.loading" />;
  }

  return (
    <View
      style={[styles.screen, {backgroundColor: theme.colors.background}]}
      testID="settings.screen"
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          styles.content,
          {paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24},
        ]}
      >
        <View style={styles.header}>
          <IconButton
            icon={<Icon name="chevronLeft" size={22} />}
            accessibilityLabel={strings.detail.back}
            onPress={() => router.back()}
            variant="surface"
            testID="settings.back"
          />
          <Text variant="displayM">{s.title}</Text>
        </View>
        {body}
        <Button
          label={strings.account.delete}
          variant="danger"
          onPress={deletion.confirm}
          loading={deletion.deleting}
          testID="settings.deleteAccount"
          style={styles.delete}
        />
      </ScrollView>
    </View>
  );
}

function SettingsForm({
  settings,
  change,
}: {
  settings: NotificationSettings;
  change: (next: NotificationSettings, now?: boolean) => Promise<boolean>;
}) {
  const set = (patch: Partial<NotificationSettings>, now = false) =>
    void change({...settings, ...patch}, now);
  const hasHome = settings.home !== null;

  return (
    <View style={styles.gap}>
      <SectionHeader title={s.section} />
      {TOGGLES.map(toggle => {
        const disabled = toggle === 'near' && !hasHome;
        return (
          <View key={toggle} style={styles.block}>
            <SwitchRow
              label={`${s.rows[toggle].icon} ${s.rows[toggle].title}`}
              hint={disabled ? s.homeRequired : s.rows[toggle].desc}
              value={settings[toggle] && !disabled}
              onChange={value => set({[toggle]: value})}
              disabled={disabled}
              testID={`settings.${toggle}`}
            />
            {toggle === 'remind' && settings.remind ? (
              <View style={styles.chips}>
                {s.when.map(option => (
                  <Chip
                    key={option.days}
                    label={option.label}
                    active={settings.remindDaysBefore === option.days}
                    onPress={() =>
                      set({remindDaysBefore: option.days as 1 | 3 | 7})
                    }
                    variant="sheet"
                    testID={`settings.remind.${option.days}`}
                  />
                ))}
              </View>
            ) : null}
            {toggle === 'near' ? (
              <HomeSection settings={settings} set={set} />
            ) : null}
          </View>
        );
      })}
      <PermissionHint />
    </View>
  );
}

function HomeSection({
  settings,
  set,
}: {
  settings: NotificationSettings;
  set: (patch: Partial<NotificationSettings>, now?: boolean) => void;
}) {
  const toast = useToast();
  const home = settings.home;
  const [editing, setEditing] = useState(home === null);
  const [text, setText] = useState('');
  const [locating, setLocating] = useState(false);
  const q = useDebouncedValue(text.trim(), 300);
  const suggestions = $api.useQuery(
    'get',
    '/v1/geocode',
    {params: {query: {q, limit: 5}}},
    {enabled: editing && q.length >= 2, staleTime: 5 * 60_000, retry: false},
  );
  const places = (suggestions.data ?? []).filter(p => p.postalCode);
  const count = $api.useQuery(
    'get',
    '/v1/events/count',
    {
      params: {
        query: {
          lat: home?.lat ?? 0,
          lon: home?.lon ?? 0,
          radiusKm: settings.nearRadiusKm,
        },
      },
    },
    {enabled: home !== null && settings.near, staleTime: 60_000},
  );

  useEffect(() => {
    if (home === null) setEditing(true);
  }, [home]);

  const useLocation = async () => {
    setLocating(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (!permission.granted) throw new Error('denied');
      const fix = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      // Rounded to ~1 km like the map; the server never stores it (E-10).
      const lat = Math.round(fix.coords.latitude * 100) / 100;
      const lon = Math.round(fix.coords.longitude * 100) / 100;
      const {data} = await fetchClient.GET('/v1/geocode/reverse', {
        params: {query: {lat, lon}},
      });
      if (!data?.postalCode) throw new Error('no postal code');
      set(
        {home: {postalCode: data.postalCode, placeName: data.city, lat, lon}},
        true,
      );
      setEditing(false);
      setText('');
      toast(s.locationTaken(data.city));
    } catch {
      toast(s.locationFailed);
    } finally {
      setLocating(false);
    }
  };

  return (
    <View style={styles.home}>
      {editing ? (
        <>
          <TextField
            label={s.home}
            value={text}
            onChangeText={setText}
            placeholder={s.homePlaceholder}
            autoCapitalize="words"
            testID="settings.home.input"
          />
          {places.map((place, index) => (
            <PlaceSuggestion
              // The geocoder may return the same ZIP code twice (e.g. two districts).
              key={`${place.postalCode}-${place.city}-${index}`}
              label={`${place.postalCode} ${place.city}`}
              onPress={() => {
                set(
                  {
                    home: {
                      postalCode: place.postalCode ?? '',
                      placeName: place.city,
                      lat: place.lat,
                      lon: place.lon,
                    },
                  },
                  true,
                );
                setEditing(false);
                setText('');
                toast(s.homeSet(place.city));
              }}
              testID={`settings.home.suggestion.${place.postalCode}`}
            />
          ))}
          {q.length >= 2 && suggestions.isSuccess && places.length === 0 ? (
            <Text variant="meta" tone="muted">
              {s.homeNoHit}
            </Text>
          ) : null}
          <LinkRow
            icon="locate"
            label={locating ? `${s.useLocation} …` : s.useLocation}
            onPress={() => void useLocation()}
            testID="settings.home.locate"
          />
        </>
      ) : home ? (
        <>
          <LinkRow
            icon="pin"
            label={s.home}
            value={`${home.postalCode} ${home.placeName}`}
            onPress={() => setEditing(true)}
            testID="settings.home"
          />
          <Button
            label={s.homeRemove}
            variant="ghost"
            onPress={() => set({home: null}, true)}
            testID="settings.home.remove"
          />
        </>
      ) : null}
      {home && settings.near ? (
        <>
          <RangeSlider
            label={s.radius(home.placeName)}
            formatValue={s.radiusValue}
            unit="km"
            value={settings.nearRadiusKm}
            onChange={value => set({nearRadiusKm: value})}
            min={5}
            max={150}
            step={5}
            caption=""
            testID="settings.radius"
          />
          {count.data ? (
            <Text variant="meta" tone="muted" testID="settings.preview">
              {s.preview(
                count.data.total,
                settings.nearRadiusKm,
                home.placeName,
              )}
            </Text>
          ) : null}
        </>
      ) : null}
    </View>
  );
}

function PermissionHint() {
  const {provider, askPermission} = usePush();
  const [state, setState] = useState<'granted' | 'ask' | 'blocked' | null>(
    null,
  );

  useEffect(() => {
    let active = true;
    void (async () => {
      const granted = await isPermissionGranted().catch(() => false);
      const canAsk = granted ? false : await canAskForPermission();
      if (active) setState(granted ? 'granted' : canAsk ? 'ask' : 'blocked');
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state === null) return null;
  return (
    <View style={styles.gap}>
      <Text variant="meta" tone="muted" testID="settings.hint">
        {state === 'granted' ? s.hintAllowed : s.hintMuted}
      </Text>
      {state === 'ask' && provider !== 'disabled' ? (
        <Button
          label={s.allow}
          variant="secondary"
          onPress={async () =>
            setState((await askPermission()) ? 'granted' : 'blocked')
          }
          testID="settings.allow"
        />
      ) : null}
      {state === 'blocked' ? (
        <Button
          label={s.openSystemSettings}
          variant="ghost"
          onPress={() => void Linking.openSettings()}
          testID="settings.systemSettings"
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  content: {paddingHorizontal: 16, gap: 16},
  header: {flexDirection: 'row', alignItems: 'center', gap: 12},
  gap: {gap: 12},
  block: {gap: 10},
  chips: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
  home: {gap: 10, paddingLeft: 4},
  delete: {marginTop: 24},
});
