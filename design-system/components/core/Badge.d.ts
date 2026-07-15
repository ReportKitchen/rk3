import * as React from "react";
export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** neutral | success ("Available now") | soon ("Coming soon") | brand. @default "neutral" */
  tone?: "neutral" | "success" | "soon" | "brand";
  /** Leading status dot. @default false */
  dot?: boolean;
  children?: React.ReactNode;
}
export function Badge(props: BadgeProps): JSX.Element;
