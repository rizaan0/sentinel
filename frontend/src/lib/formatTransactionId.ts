/**
 * Short, scannable reference from a UUID transaction id.
 * Full id stays available via title/copy — never mutate the underlying value.
 */
export function formatTransactionRef(id: string): string {
  const hex = id.replace(/-/g, "").toUpperCase();
  if (hex.length < 8) return id;
  return `${hex.slice(0, 4)}-${hex.slice(4, 8)}`;
}
