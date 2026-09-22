import { describe, expect, it } from "vitest";
import { formatAccountNumber } from "./formatAccountNumber";

describe("formatAccountNumber", () => {
  it("groups a 12-digit account into fours", () => {
    expect(formatAccountNumber("123456789012")).toBe("1234 5678 9012");
  });

  it("strips non-digits before grouping", () => {
    expect(formatAccountNumber("1234-5678-9012")).toBe("1234 5678 9012");
  });
});
