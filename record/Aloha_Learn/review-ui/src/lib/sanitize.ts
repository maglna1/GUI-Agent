const LABEL_MAX_LEN = 30;
const SPECIAL_CHARS = /[\\:?*]/g;

export function sanitize(raw: string): string {
  if (!raw) throw new Error("label is empty");
  let s = raw.trim().toLowerCase();
  s = s.replaceAll("\\", "-").replaceAll("/", "-");
  s = s.replace(SPECIAL_CHARS, "");
  s = s.replace(/\s+/g, "_");
  s = s.replace(/-+/g, "-");
  s = s.replace(/_+/g, "_");
  // Strip any leading/trailing run of "-" or "_" (any order) in a single pass,
  // matching Python's .strip("-_") which is order-independent.
  s = s.replace(/^[-_]+|[-_]+$/g, "");
  s = s.slice(0, LABEL_MAX_LEN).replace(/[-_]+$/, "");
  if (!s) throw new Error(`label '${raw}' has no safe characters after sanitization`);
  return s;
}

export function isValidLabel(s: string): boolean {
  if (!s) return false;
  if (s.length > LABEL_MAX_LEN) return false;
  return /^[a-z0-9_]+$/.test(s);
}
