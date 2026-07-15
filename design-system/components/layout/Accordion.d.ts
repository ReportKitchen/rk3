import * as React from "react";
export interface AccordionItem { q: React.ReactNode; a: React.ReactNode; }
export interface AccordionProps extends React.HTMLAttributes<HTMLDivElement> {
  items: AccordionItem[];
  /** Allow multiple panels open. @default false */
  multi?: boolean;
  /** Indices open on mount. @default [0] */
  defaultOpen?: number[];
}
/** Layered/expandable content — makes long toolkits scannable. */
export function Accordion(props: AccordionProps): JSX.Element;
