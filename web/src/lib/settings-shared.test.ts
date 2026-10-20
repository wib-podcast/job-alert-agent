import { describe, expect, it } from "vitest";

import { DEFAULTS, csvToList, estimateQueries, isSettingKey, listToCsv } from "./settings-shared";

const base = { ...DEFAULTS } as Record<string, string>;

function withSettings(overrides: Record<string, string>) {
  return { ...base, ...overrides } as never;
}

describe("csv helpers", () => {
  it("trims and drops empties in both directions", () => {
    expect(csvToList(" a , b ,, c ")).toEqual(["a", "b", "c"]);
    expect(listToCsv([" a ", "", "b"])).toBe("a,b");
  });

  it("round-trips", () => {
    expect(csvToList(listToCsv(["Product Manager", "AI PM"]))).toEqual([
      "Product Manager",
      "AI PM",
    ]);
  });
});

describe("isSettingKey", () => {
  it("accepts known keys and rejects anything else", () => {
    expect(isSettingKey("TARGET_ROLES")).toBe(true);
    // Guards the settings table against arbitrary form fields.
    expect(isSettingKey("ANTHROPIC_API_KEY")).toBe(false);
    expect(isSettingKey("__proto__")).toBe(false);
  });
});

describe("estimateQueries", () => {
  it("counts roles × locations for location-aware sources", () => {
    const s = withSettings({
      TARGET_ROLES: "a,b",
      TARGET_LOCATIONS: "x,y,z",
      ENABLE_IIMJOBS: "true",
      ENABLE_MYCAREERSFUTURE: "false",
      ENABLE_LINKEDIN: "false",
      ENABLE_GOOGLE_JOBS: "false",
    });
    expect(estimateQueries(s)).toBe(6);
  });

  it("counts MyCareersFuture once per role, not per location", () => {
    /* It is Singapore by definition and ignores the location list — counting it
       per location would overstate the estimate by the location count. */
    const s = withSettings({
      TARGET_ROLES: "a,b",
      TARGET_LOCATIONS: "x,y,z",
      ENABLE_IIMJOBS: "false",
      ENABLE_MYCAREERSFUTURE: "true",
      ENABLE_LINKEDIN: "false",
      ENABLE_GOOGLE_JOBS: "false",
    });
    expect(estimateQueries(s)).toBe(2);
  });

  it("adds the two kinds of source together", () => {
    const s = withSettings({
      TARGET_ROLES: "a,b",
      TARGET_LOCATIONS: "x,y",
      ENABLE_IIMJOBS: "true",
      ENABLE_MYCAREERSFUTURE: "true",
      ENABLE_LINKEDIN: "false",
      ENABLE_GOOGLE_JOBS: "false",
    });
    expect(estimateQueries(s)).toBe(2 * 2 + 2);
  });

  it("is zero when every source is off", () => {
    const s = withSettings({
      ENABLE_IIMJOBS: "false",
      ENABLE_MYCAREERSFUTURE: "false",
      ENABLE_LINKEDIN: "false",
      ENABLE_GOOGLE_JOBS: "false",
    });
    expect(estimateQueries(s)).toBe(0);
  });

  it("treats an empty location list as one, so a source still counts", () => {
    const s = withSettings({
      TARGET_ROLES: "a",
      TARGET_LOCATIONS: "",
      ENABLE_IIMJOBS: "true",
      ENABLE_MYCAREERSFUTURE: "false",
      ENABLE_LINKEDIN: "false",
      ENABLE_GOOGLE_JOBS: "false",
    });
    expect(estimateQueries(s)).toBe(1);
  });
});
