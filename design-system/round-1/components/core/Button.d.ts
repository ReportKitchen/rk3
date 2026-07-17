import * as React from "react";
/**
 * Primary action control.
 * @startingPoint section="Actions" subtitle="Buttons: primary, secondary, accent, ghost" viewport="700x150"
 */
export interface ButtonProps extends React.HTMLAttributes<HTMLElement> {
  /** Visual style. @default "primary" */
  variant?: "primary" | "secondary" | "accent" | "ghost";
  /** @default "md" */
  size?: "sm" | "md" | "lg";
  /** Fully rounded pill shape. @default false */
  pill?: boolean;
  /** Lucide icon id shown before the label */
  iconLeft?: string;
  /** Lucide icon id shown after the label */
  iconRight?: string;
  /** Render as <a> with this href instead of <button> */
  href?: string;
  disabled?: boolean;
  /** Stretch to container width. @default false */
  full?: boolean;
  children?: React.ReactNode;
}
/**
 * Primary action control.
 */
export function Button(props: ButtonProps): JSX.Element;
