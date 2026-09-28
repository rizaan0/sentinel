/** Symmetric page inset. Keeps the rail on the viewport center. */
export const LANDING_PAD = "px-4 sm:px-8";

/** One centered column for the navbar, hero, and footer. */
export const LANDING_FRAME = "mx-auto w-full max-w-5xl";

/** Rail plus inset, for content that should sit inside the frame edges. */
export const LANDING_CHROME = `${LANDING_FRAME} ${LANDING_PAD}`;

/** Hero measure — same frame as the navbar and footer. */
export const LANDING_CONTENT = LANDING_FRAME;
