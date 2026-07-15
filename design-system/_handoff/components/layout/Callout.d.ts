import * as React from "react";
/**
 * Full-width CTA band. The primary conversion moment on marketing pages.
 * @startingPoint section="Marketing" subtitle="Full-width CTA band with whisk accent" viewport="1000x300"
 */
export interface CalloutProps extends React.HTMLAttributes<HTMLDivElement> {
  eyebrow?: string;
  title: string;
  primaryLabel?: string;
  primaryHref?: string;
  onClickPrimary?: React.MouseEventHandler;
  secondaryLabel?: string;
  secondaryHref?: string;
  onClickSecondary?: React.MouseEventHandler;
  /** @default "rhino" */
  tone?: "rhino" | "tomato" | "cream";
  /** Faint whisk accent in corner (sanctioned decorative use). @default true */
  whisk?: boolean;
  children?: React.ReactNode;
}
/**
 * Full-width CTA band. The primary conversion moment on marketing pages.
 */
export function Callout(props: CalloutProps): JSX.Element;
