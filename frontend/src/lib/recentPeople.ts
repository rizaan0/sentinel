import type { TransactionSummary } from "./types";

export type RecentPerson = {
  account_number: string;
  full_name: string;
};

/** Unique counterparties from newest history first (GPay-style recent people). */
export function recentPeopleFromHistory(
  items: TransactionSummary[],
  limit = 8,
): RecentPerson[] {
  const seen = new Set<string>();
  const people: RecentPerson[] = [];
  for (const tx of items) {
    if (seen.has(tx.counterparty_account_number)) continue;
    seen.add(tx.counterparty_account_number);
    people.push({
      account_number: tx.counterparty_account_number,
      full_name: tx.counterparty_name,
    });
    if (people.length >= limit) break;
  }
  return people;
}

export function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
