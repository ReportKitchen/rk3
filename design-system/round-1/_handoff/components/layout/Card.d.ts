import * as React from "react";
/**
 * "Our Work" project tile — photo-free color-block cover.
 * @startingPoint section="Content" subtitle="Project card for Our Work grids" viewport="420x400"
 */
export interface CardProps extends React.HTMLAttributes<HTMLAnchorElement> {
  title: string;
  description?: string;
  /** Client / org name shown as a tomato kicker */
  client?: string;
  tags?: string[];
  /** CSS color for the photo-free cover block. @default rhino */
  coverColor?: string;
  /** Lucide icon id shown large on the cover. @default "file-text" */
  coverIcon?: string;
  /** Small uppercase label bottom-left of the cover (e.g. "Toolkit") */
  coverText?: string;
  href?: string;
}
/**
 * "Our Work" project tile — photo-free color-block cover.
 */
export function Card(props: CardProps): JSX.Element;
