import { describe, it, expect } from "vitest";
import { sanitize, isValidLabel } from "./sanitize";

describe("sanitize", () => {
  it("lowercases and replaces spaces with underscores", () => {
    expect(sanitize("Start Button")).toBe("start_button");
  });

  it("replaces slashes and backslashes with dash", () => {
    expect(sanitize("a/b\\c")).toBe("a-b-c");
  });

  it("strips backslash, colon, question mark, asterisk", () => {
    expect(sanitize("a:b?c*d")).toBe("abcd");
  });

  it("truncates to 30 chars", () => {
    expect(sanitize("a".repeat(50)).length).toBe(30);
  });

  it("collapses multiple dashes and underscores", () => {
    expect(sanitize("Clone  Repository__Tab")).toBe("clone_repository_tab");
  });

  it("throws on empty string", () => {
    expect(() => sanitize("")).toThrow();
  });

  it("throws when all chars are special", () => {
    expect(() => sanitize("///??**")).toThrow();
  });
});

describe("isValidLabel", () => {
  it("accepts snake_case strings", () => {
    expect(isValidLabel("start_button")).toBe(true);
  });

  it("rejects empty and strings over 30 chars", () => {
    expect(isValidLabel("")).toBe(false);
    expect(isValidLabel("a".repeat(31))).toBe(false);
  });

  it("rejects strings with disallowed chars", () => {
    expect(isValidLabel("Start-Button")).toBe(false);
    expect(isValidLabel("foo bar")).toBe(false);
  });
});
