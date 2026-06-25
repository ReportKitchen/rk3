import { createContext } from "react";

// Bridges LandingMaker's live state/handlers to RightPanel, which Puck renders
// via a *stable* overrides.fields slot. Using context (not override props) keeps
// the override identity stable while still delivering fresh values.
export const LandingCtx = createContext({});
