import * as React from "react";
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  /** Lucide icon id shown inside the field */
  icon?: string;
  helper?: string;
  error?: string;
}
export function Input(props: InputProps): JSX.Element;
