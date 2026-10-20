import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { checkPasscode, isAllowed, ownerEmail, safeEqual } from "./allowlist";

const ORIGINAL = { ...process.env };

beforeEach(() => {
  delete process.env.ALLOWED_EMAILS;
  delete process.env.APP_PASSCODE;
});

afterEach(() => {
  process.env = { ...ORIGINAL };
});

describe("isAllowed", () => {
  it("admits an address on the list", () => {
    process.env.ALLOWED_EMAILS = "ayan@example.com";
    expect(isAllowed("ayan@example.com")).toBe(true);
  });

  it("ignores case and surrounding whitespace", () => {
    process.env.ALLOWED_EMAILS = "  Ayan@Example.com , other@example.com ";
    expect(isAllowed("AYAN@EXAMPLE.COM")).toBe(true);
    expect(isAllowed("other@example.com")).toBe(true);
  });

  it("refuses an address that isn't listed", () => {
    process.env.ALLOWED_EMAILS = "ayan@example.com";
    expect(isAllowed("someone@else.com")).toBe(false);
  });

  it("refuses everyone when the allowlist is empty — it never means allow-all", () => {
    process.env.ALLOWED_EMAILS = "";
    expect(isAllowed("ayan@example.com")).toBe(false);
  });

  it("refuses everyone when the allowlist is unset", () => {
    expect(isAllowed("ayan@example.com")).toBe(false);
  });

  it("refuses a missing address", () => {
    process.env.ALLOWED_EMAILS = "ayan@example.com";
    expect(isAllowed(null)).toBe(false);
    expect(isAllowed(undefined)).toBe(false);
    expect(isAllowed("")).toBe(false);
  });
});

describe("safeEqual", () => {
  it("matches identical strings and rejects everything else", () => {
    expect(safeEqual("hunter2", "hunter2")).toBe(true);
    expect(safeEqual("hunter2", "hunter3")).toBe(false);
    expect(safeEqual("hunter2", "hunter22")).toBe(false);
    expect(safeEqual("", "")).toBe(true);
  });
});

describe("ownerEmail", () => {
  it("is the first address on the allowlist", () => {
    process.env.ALLOWED_EMAILS = "first@example.com,second@example.com";
    expect(ownerEmail()).toBe("first@example.com");
  });

  it("is null with no allowlist", () => {
    expect(ownerEmail()).toBeNull();
  });
});

describe("checkPasscode", () => {
  beforeEach(() => {
    process.env.ALLOWED_EMAILS = "ayan@example.com";
    process.env.APP_PASSCODE = "correct horse";
  });

  it("grants the owner identity for the right passcode", () => {
    expect(checkPasscode("correct horse")).toEqual({ email: "ayan@example.com" });
  });

  it("refuses a wrong passcode", () => {
    expect(checkPasscode("wrong horse")).toBeNull();
  });

  it("refuses an empty or non-string passcode", () => {
    expect(checkPasscode("")).toBeNull();
    expect(checkPasscode(undefined)).toBeNull();
    expect(checkPasscode(12345)).toBeNull();
  });

  it("refuses everything when no passcode is configured", () => {
    delete process.env.APP_PASSCODE;
    expect(checkPasscode("anything")).toBeNull();
    expect(checkPasscode("")).toBeNull();
  });

  it("refuses when there is no allowlisted identity to grant", () => {
    delete process.env.ALLOWED_EMAILS;
    expect(checkPasscode("correct horse")).toBeNull();
  });
});
