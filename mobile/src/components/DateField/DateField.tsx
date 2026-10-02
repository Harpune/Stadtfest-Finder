import DateTimePicker, {
  DateTimePickerAndroid,
  type DateTimePickerEvent,
} from '@react-native-community/datetimepicker';
import React, {useState} from 'react';
import {Modal, Platform, Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Button} from '../Button/Button';
import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface DateFieldProps {
  /** Small label above the field, e.g. "Beginn". */
  label: string;
  /** ISO date `YYYY-MM-DD` or null. */
  value: string | null;
  onChange: (value: string) => void;
  placeholder: string;
  /** Marks the field red; the text is shown by the caller below both date fields. */
  invalid?: boolean;
  /** Earliest date that can be picked (e.g. the start for the end date). */
  minimumDate?: string | null;
  testID: string;
}

function toDate(iso: string): Date {
  const [year = 1970, month = 1, day = 1] = iso.split('-').map(Number);
  return new Date(year, month - 1, day, 12);
}

function toIso(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** "2026-10-03" → "03.10.2026" */
export function formatGermanDate(iso: string): string {
  const [year, month, day] = iso.split('-');
  return `${day}.${month}.${year}`;
}

/**
 * Date field with the system date picker (R07-US3): Android opens its dialog, iOS shows
 * the inline calendar in a sheet with "Fertig".
 */
export function DateField({
  label,
  value,
  onChange,
  placeholder,
  invalid = false,
  minimumDate,
  testID,
}: DateFieldProps) {
  const theme = useTheme();
  const c = theme.colors;
  const [iosOpen, setIosOpen] = useState(false);
  const [draft, setDraft] = useState<Date>(() =>
    toDate(value ?? toIso(new Date())),
  );
  const initial = value ?? minimumDate ?? toIso(new Date());
  const minimum = minimumDate ? toDate(minimumDate) : undefined;

  const open = () => {
    if (Platform.OS === 'android') {
      DateTimePickerAndroid.open({
        value: toDate(initial),
        mode: 'date',
        minimumDate: minimum,
        onChange: (event: DateTimePickerEvent, date?: Date) => {
          if (event.type === 'set' && date) onChange(toIso(date));
        },
      });
      return;
    }
    setDraft(toDate(initial));
    setIosOpen(true);
  };

  return (
    <View style={styles.container}>
      <Text variant="meta" tone="muted">
        {label}
      </Text>
      <Pressable
        testID={testID}
        accessibilityRole="button"
        accessibilityLabel={`${label}, ${value ? formatGermanDate(value) : placeholder}`}
        onPress={open}
        style={({pressed}) => [
          styles.field,
          {
            backgroundColor: c.surface,
            borderColor: invalid ? c.error : c.outline,
            borderRadius: theme.radius.input,
            opacity: pressed ? 0.85 : 1,
          },
        ]}
      >
        <Text
          variant="body"
          tone={value ? 'default' : 'muted'}
          style={styles.value}
          testID={`${testID}.value`}
        >
          {value ? formatGermanDate(value) : placeholder}
        </Text>
        <Icon name="calendar" size={20} color={c.onSurfaceMuted} />
      </Pressable>
      {Platform.OS === 'ios' ? (
        <Modal
          visible={iosOpen}
          transparent
          animationType="fade"
          onRequestClose={() => setIosOpen(false)}
        >
          <View style={[styles.scrim, {backgroundColor: c.scrim}]}>
            <View
              style={[
                styles.sheet,
                {backgroundColor: c.surface, borderRadius: theme.radius.sheet},
              ]}
            >
              <DateTimePicker
                value={draft}
                mode="date"
                display="inline"
                locale="de-DE"
                minimumDate={minimum}
                accentColor={c.mod.primary}
                themeVariant={theme.scheme}
                onChange={(_event, date) => {
                  if (date) setDraft(date);
                }}
                testID={`${testID}.picker`}
              />
              <Button
                label={strings.common.done}
                variant="mod"
                onPress={() => {
                  setIosOpen(false);
                  onChange(toIso(draft));
                }}
                testID={`${testID}.done`}
              />
            </View>
          </View>
        </Modal>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, gap: 6},
  field: {
    height: 52,
    borderWidth: 1,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
  },
  value: {flex: 1, fontSize: 16},
  scrim: {flex: 1, justifyContent: 'center', padding: 16},
  sheet: {padding: 12, gap: 8},
});
