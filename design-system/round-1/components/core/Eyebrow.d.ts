import * as React from "react";
export interface EyebrowProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** @default "tomato" */
  color?: "tomato" | "macaroni" | "muffin" | "white";
  /** Leading tick mark. @default true */
  tick?: boolean;
  children?: React.ReactNode;
}
export function Eyebrow(props: EyebrowProps): JSX.Element;
