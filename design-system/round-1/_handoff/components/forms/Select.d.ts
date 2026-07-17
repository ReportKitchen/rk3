import * as React from "react";
export type SelectOption = string | { value: string; label: string };
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  placeholder?: string;
  helper?: string;
}
export function Select(props: SelectProps): JSX.Element;
