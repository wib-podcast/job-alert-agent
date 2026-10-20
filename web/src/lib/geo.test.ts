import { describe, expect, it } from "vitest";

import { GEOS, compareJobs, geoFor, geoLabel, isTargetGeo } from "./geo";

describe("geo ordering", () => {
  it("lists the target markets in the owner's priority order", () => {
    const targets = GEOS.filter((g) => g.priority <= 7).map((g) => g.code);
    expect(targets).toEqual(["AE", "SG", "GB", "IE", "TH", "MY", "VN"]);
  });

  it("ranks India last so local roles never outrank an international one", () => {
    expect(geoFor("IN").priority).toBeGreaterThan(geoFor("VN").priority);
  });

  it("treats India as home, not a target market", () => {
    expect(isTargetGeo("IN")).toBe(false);
    expect(isTargetGeo("AE")).toBe(true);
  });

  it("is case-insensitive about codes a scraper might emit", () => {
    expect(geoFor("ae").label).toBe("UAE");
  });

  it("sorts an unknown code last instead of throwing", () => {
    expect(geoFor("ZZ").priority).toBe(100);
    expect(geoFor(null).priority).toBe(100);
  });
});

describe("board ranking", () => {
  it("puts the higher score first regardless of geography", () => {
    const local = { relevanceScore: 9, geo: "IN" };
    const dubai = { relevanceScore: 6, geo: "AE" };
    expect([dubai, local].sort(compareJobs)).toEqual([local, dubai]);
  });

  it("breaks a score tie by geography priority", () => {
    const sg = { relevanceScore: 8, geo: "SG" };
    const ae = { relevanceScore: 8, geo: "AE" };
    expect([sg, ae].sort(compareJobs)).toEqual([ae, sg]);
  });
});

describe("geoLabel", () => {
  it("renders flag and name for a known market", () => {
    expect(geoLabel("AE")).toBe("🇦🇪 UAE");
  });

  it("is case-insensitive, since codes arrive from scrapers", () => {
    expect(geoLabel("sg")).toBe("🇸🇬 Singapore");
  });

  it("falls back to a globe and the raw code for anything unrecognised", () => {
    expect(geoLabel("ZZ")).toBe("🌍 ZZ");
  });
});
