import {createContext, useContext} from 'react';

/** True inside a `BottomSheet`; inputs there must report the keyboard to the sheet. */
export const InSheetContext = createContext(false);

/** Whether the calling component is rendered inside a `BottomSheet`. */
export function useInSheet(): boolean {
  return useContext(InSheetContext);
}
