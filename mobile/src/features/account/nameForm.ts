/** Name input rules, mirroring PATCH /v1/me (1-50 characters after trimming). */
import {useState} from 'react';

export const NAME_MAX_LENGTH = 50;

export function isValidName(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.length >= 1 && trimmed.length <= NAME_MAX_LENGTH;
}

export interface NameFormState {
  firstName: string;
  lastName: string;
  setFirstName: (value: string) => void;
  setLastName: (value: string) => void;
  /** True after a submit attempt with invalid input: show field errors. */
  showErrors: boolean;
  firstNameValid: boolean;
  lastNameValid: boolean;
  /** Marks the form as submitted; returns the trimmed names if both are valid. */
  submit: () => {firstName: string; lastName: string} | null;
}

export function useNameForm(
  initialFirst = '',
  initialLast = '',
): NameFormState {
  const [firstName, setFirstName] = useState(initialFirst);
  const [lastName, setLastName] = useState(initialLast);
  const [showErrors, setShowErrors] = useState(false);
  const firstNameValid = isValidName(firstName);
  const lastNameValid = isValidName(lastName);
  return {
    firstName,
    lastName,
    setFirstName,
    setLastName,
    showErrors,
    firstNameValid,
    lastNameValid,
    submit: () => {
      setShowErrors(true);
      if (!firstNameValid || !lastNameValid) return null;
      return {firstName: firstName.trim(), lastName: lastName.trim()};
    },
  };
}
