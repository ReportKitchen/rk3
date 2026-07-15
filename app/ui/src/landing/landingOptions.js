import { createContext, useContext } from "react";

// Per-document options for the custom fields: the document's detected summary
// sections and its figures.
//
// This exists because Puck gives a custom field's render() only
// { field, name, id, value, onChange, readOnly } — no metadata — and usePuck()
// doesn't expose metadata either. So a custom field has no route to per-document
// data, and needs one handed to it. (The block *components* are fine: Puck does
// pass metadata to render(). It's only fields that are cut off.)
//
// Everything else per-document still travels through Puck's metadata; this
// carries only what fields need.
export const LandingOptions = createContext({ summarySections: [], images: [] });

export const useLandingOptions = () => useContext(LandingOptions);
