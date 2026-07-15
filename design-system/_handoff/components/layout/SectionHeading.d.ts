import * as React from "react";
export interface SectionHeadingProps extends React.HTMLAttributes<HTMLDivElement> {
  eyebrow?: string;
  eyebrowColor?: "tomato" | "macaroni" | "muffin";
  title: string;
  intro?: string;
  /** @default "left" */
  align?: "left" | "center";
  /** For dark/rhino grounds. @default false */
  inverse?: boolean;
  /** Title size. @default "lg" */
  size?: "sm" | "md" | "lg";
}
export function SectionHeading(props: SectionHeadingProps): JSX.Element;
