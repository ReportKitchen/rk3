import { useEffect, useState } from "react";

// True only once `active` has stayed true for `delay` ms — so a loading indicator
// NEVER flashes for a sub-second wait. If `active` clears before the delay, the
// flag never trips. Used to gate every whisk loader: it appears only when we're
// genuinely waiting on the AI, never for something that resolves instantly.
export function useDelayed(active, delay = 350) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!active) { setShown(false); return undefined; }
    const id = setTimeout(() => setShown(true), delay);
    return () => clearTimeout(id);
  }, [active, delay]);
  return shown;
}
