export const CONTROL_H = 36;

export function radiusFor(height: number): number {
  return Math.round(height * 0.42);
}

export const TEXT = 14;
export const TRACKING = -0.3;

/** iOS corner from the reference: smoothing 0.6, exponent 5. */
export const IOS_SMOOTHING = 0.6;
