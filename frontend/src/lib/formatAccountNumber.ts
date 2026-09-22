/**
 * Groups a Sentinel account number for display (e.g. 123456789012 → 1234 5678 9012).
 * Does not alter the underlying value used for copy/API.
 */
export function formatAccountNumber(accountNumber: string): string {
  const digits = accountNumber.replace(/\D/g, "");
  if (digits.length === 0) return accountNumber;
  return digits.replace(/(\d{4})(?=\d)/g, "$1 ").trim();
}
