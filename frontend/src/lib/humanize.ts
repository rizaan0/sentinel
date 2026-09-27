const ACRONYMS = new Set(["ml", "ai", "id", "pin", "st"]);

/** Turn a stored code into a sentence. Values without underscores are left unchanged. */
export function humanizeLabel(value: string): string {
  if (!value.includes("_")) return value;
  return value
    .split("_")
    .filter(Boolean)
    .map((word, index) => {
      const lower = word.toLowerCase();
      if (ACRONYMS.has(lower)) return lower.toUpperCase();
      if (index === 0) return lower.charAt(0).toUpperCase() + lower.slice(1);
      return lower;
    })
    .join(" ");
}
