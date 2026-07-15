import * as React from "react";
export interface TagProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** @default "neutral" */
  tone?: "neutral" | "tomato" | "macaroni" | "muffin" | "rhino";
  /** Adds hover affordance for filter chips. @default false */
  interactive?: boolean;
  /** Selected/pressed filter state. @default false */
  active?: boolean;
  children?: React.ReactNode;
}
export function Tag(props: TagProps): JSX.Element;
