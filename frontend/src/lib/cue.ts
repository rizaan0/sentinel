import { bind, play, setEnabled, setVolume, type SoundName } from "cuelume";

let started = false;

/**
 * Tasteful Sentinel sound layer — bind once, then use imperative cues
 * for meaningful success/error moments. Safe in SSR and test envs.
 */
export function initCue() {
  if (started || typeof window === "undefined") return;
  started = true;

  const reduced =
    window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
  setEnabled(!reduced);
  setVolume(0.55);
  bind();
}

function safePlay(name: SoundName, volume?: number) {
  try {
    play(name, volume == null ? undefined : { volume });
  } catch {
    // Web Audio may be blocked; never break UI flow.
  }
}

export const cue = {
  /** Payment completed, account created, PIN set */
  success(kind: "default" | "payment" | "auth" = "default") {
    const volume = kind === "payment" ? 0.5 : kind === "auth" ? 0.38 : 0.4;
    safePlay("success", volume);
  },
  /** Wrong password/PIN, failed transfer, validation refusal */
  error() {
    safePlay("error", 0.36);
  },
  /** Clipboard copy confirmed */
  copy() {
    safePlay("success", 0.28);
  },
  /** User-initiated work beginning (transfer authorize, search) */
  loading() {
    safePlay("loading", 0.22);
  },
  /** Soft dismiss / logout */
  dismiss() {
    safePlay("droplet", 0.25);
  },
};
