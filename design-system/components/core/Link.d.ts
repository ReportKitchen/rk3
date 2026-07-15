import * as React from "react";
export interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  /** "macaroni" gives a thick highlight underline. @default "default" */
  emphasis?: "default" | "macaroni";
  children?: React.ReactNode;
}
export function Link(props: LinkProps): JSX.Element;
