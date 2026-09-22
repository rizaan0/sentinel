import { describe, expect, it } from "vitest";
import { formatTransactionRef } from "./formatTransactionId";

describe("formatTransactionRef", () => {
  it("shortens a UUID to an 8-character grouped reference", () => {
    expect(formatTransactionRef("a1b2c3d4-e5f6-7890-abcd-ef1234567890")).toBe("A1B2-C3D4");
  });

  it("returns short ids unchanged", () => {
    expect(formatTransactionRef("tx-123")).toBe("tx-123");
  });
});
