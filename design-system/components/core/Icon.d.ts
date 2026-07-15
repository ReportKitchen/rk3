import * as React from "react";
export interface IconProps extends React.HTMLAttributes<HTMLElement> {
  /** Lucide icon id, e.g. "arrow-right", "upload", "file-text". */
  name: string;
  /** px. @default 20 */
  size?: number;
  /** @default 2 */
  strokeWidth?: number;
  /** @default "currentColor" */
  color?: string;
}
/** Wrapper over Lucide. Page must load the lucide script once. */
export function Icon(props: IconProps): JSX.Element;
