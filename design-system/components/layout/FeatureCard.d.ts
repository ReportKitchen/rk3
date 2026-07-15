import * as React from "react";
/**
 * Offering / value-prop card with icon tile, badge and action link.
 * @startingPoint section="Content" subtitle="Offering & value-prop card" viewport="420x320"
 */
export interface FeatureCardProps extends React.HTMLAttributes<HTMLElement> {
  /** Lucide icon id. @default "sparkles" */
  icon?: string;
  title: string;
  /** Availability badge label (e.g. "Available now", "Coming soon") */
  badge?: string;
  badgeTone?: "success" | "soon" | "brand";
  /** Trailing action link label; presence renders the card as a link */
  action?: string;
  href?: string;
  /** Icon-tile accent color. @default "tomato" */
  accent?: "tomato" | "macaroni" | "muffin" | "rhino";
  children?: React.ReactNode;
}
/**
 * Offering / value-prop card with icon tile, badge and action link.
 */
export function FeatureCard(props: FeatureCardProps): JSX.Element;
