import { describe, expect, it } from "vitest";

import { formatSeconds, toneForLoadState } from "../lib/format";

describe("formatSeconds", () => {
  it("renders none for missing or zero values", () => {
    expect(formatSeconds(undefined)).toBe("none");
    expect(formatSeconds(null)).toBe("none");
    expect(formatSeconds(0)).toBe("none");
  });

  it("rounds positive seconds", () => {
    expect(formatSeconds(2.4)).toBe("2s");
    expect(formatSeconds(2.6)).toBe("3s");
  });
});

describe("toneForLoadState", () => {
  it("maps states to tones", () => {
    expect(toneForLoadState("high cognitive load")).toBe("rose");
    expect(toneForLoadState("medium cognitive load")).toBe("amber");
    expect(toneForLoadState("low cognitive load")).toBe("emerald");
  });

  it("defaults to slate for unknown values", () => {
    expect(toneForLoadState("")).toBe("slate");
    expect(toneForLoadState(undefined)).toBe("slate");
  });
});
