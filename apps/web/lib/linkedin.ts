/** LinkedIn personal-profile URL normalize + validate (mirrors API). */

const MSG = "Enter a LinkedIn profile URL like https://www.linkedin.com/in/username";

export function normalizeLinkedInUrl(value: string): string | null {
  const raw = value.trim();
  if (!raw) return null;

  let candidate = raw;
  const lower = candidate.toLowerCase();
  if (!lower.startsWith("http://") && !lower.startsWith("https://")) {
    if (lower.startsWith("linkedin.com/") || lower.startsWith("www.linkedin.com/")) {
      candidate = `https://${candidate}`;
    } else {
      throw new Error(MSG);
    }
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error(MSG);
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(MSG);
  }

  const host = parsed.hostname.toLowerCase();
  if (host !== "linkedin.com" && host !== "www.linkedin.com") {
    throw new Error(MSG);
  }

  const parts = parsed.pathname.split("/").filter(Boolean);
  if (parts.length < 2 || parts[0]!.toLowerCase() !== "in") {
    throw new Error(MSG);
  }

  const username = parts[1]!;
  if (!username || !/^[A-Za-z0-9_-]+$/.test(username)) {
    throw new Error(MSG);
  }

  return `https://www.linkedin.com/in/${username}/`;
}

export function linkedInUrlSchemaRefine(value: string): boolean {
  if (!value.trim()) return true;
  try {
    return normalizeLinkedInUrl(value) !== null;
  } catch {
    return false;
  }
}

export const LINKEDIN_URL_MESSAGE = MSG;
