/**
 * "Konto löschen" with confirmation (R05-US6). Used on the account page and, from R11 on,
 * in the notification settings.
 */
import {useCallback, useState} from 'react';
import {Alert} from 'react-native';

import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';

export function useConfirmDeleteAccount() {
  const {deleteAccount} = useAuth();
  const [deleting, setDeleting] = useState(false);

  const confirm = useCallback(() => {
    Alert.alert(strings.account.deleteTitle, strings.account.deleteText, [
      {text: strings.account.cancel, style: 'cancel'},
      {
        text: strings.account.deleteConfirm,
        style: 'destructive',
        onPress: async () => {
          setDeleting(true);
          const deleted = await deleteAccount();
          if (!deleted) setDeleting(false);
        },
      },
    ]);
  }, [deleteAccount]);

  return {confirm, deleting};
}
