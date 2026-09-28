// Shared motion tokens. Easing curves mirror the CSS custom properties in
// globals.css; springs are the canonical physics used across components.
// Strong custom variants — defaults like `ease-in`/`ease-out` feel weak.

export const EASE_OUT = [0.16, 1, 0.3, 1] as const;
export const EASE_IN_OUT = [0.77, 0, 0.175, 1] as const;
export const EASE_DRAWER = [0.32, 0.72, 0, 1] as const;

/** CSS string form of EASE_OUT for inline style transitions. */
export const EASE_OUT_CSS = "cubic-bezier(0.16, 1, 0.3, 1)";
