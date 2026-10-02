/** "Feste automatisch suchen" (09-01, R10-US1): postal code with place name, start. */
import React, {useState} from 'react';
import {StyleSheet, View} from 'react-native';

import {$api} from '@/api/client';
import {BottomSheet, Button, Text, TextField} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {useAiSearch} from './AiSearchProvider';

const POSTAL_CODE = /^[0-9]{5}$/;

type ErrorCode = keyof typeof strings.mod.ai.errors;

export function AiSearchSheet({
  visible,
  onClose,
}: {
  visible: boolean;
  onClose: () => void;
}) {
  const theme = useTheme();
  const {start} = useAiSearch();
  const [code, setCode] = useState('');
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const valid = POSTAL_CODE.test(code);
  const place = $api.useQuery(
    'get',
    '/v1/geocode',
    {params: {query: {q: code, limit: 1}}},
    {enabled: valid, staleTime: 5 * 60_000, retry: false},
  );
  const match = place.data?.find(item => item.postalCode === code);
  const unknown = valid && place.isSuccess && !match;

  const error =
    serverError ??
    (touched && code.length > 0 && !valid
      ? strings.mod.ai.postalInvalid
      : unknown
        ? strings.mod.ai.postalUnknown
        : undefined);

  const submit = async () => {
    setBusy(true);
    const result = await start(code);
    setBusy(false);
    if (result.ok || result.status === 409) {
      setCode('');
      setTouched(false);
      onClose();
      return;
    }
    const known = result.error?.error as ErrorCode | undefined;
    setServerError(
      known && known in strings.mod.ai.errors
        ? strings.mod.ai.errors[known]
        : strings.mod.toast.failed,
    );
  };

  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={strings.mod.ai.sheetTitle}
      testID="mod.ai.sheet"
      footer={
        <Button
          label={strings.mod.ai.start}
          variant="mod"
          onPress={() => void submit()}
          disabled={!valid || unknown}
          loading={busy}
          testID="mod.ai.start"
          style={styles.button}
        />
      }
    >
      <Text variant="body" tone="muted">
        {strings.mod.ai.sheetText}
      </Text>
      <View style={styles.field}>
        <TextField
          label={strings.mod.ai.postalCode}
          value={code}
          onChangeText={text => {
            setCode(text.replace(/[^0-9]/g, '').slice(0, 5));
            setServerError(null);
          }}
          onSubmitEditing={() => setTouched(true)}
          keyboardType="number-pad"
          maxLength={5}
          variant="code"
          accentColor={valid && !unknown ? theme.colors.mod.primary : undefined}
          error={error}
          testID="mod.ai.postalCode"
        />
        {match ? (
          <Text variant="body" tone="mod" testID="mod.ai.place">
            {match.city}
          </Text>
        ) : null}
      </View>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  field: {gap: 6},
  button: {flex: 1},
});
