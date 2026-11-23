/** Mirrors app/core/security.py password_problems(); the API is the source of truth. */
export const MIN_PASSWORD_LENGTH = 12;

const COMMON = [
  "password",
  "passw0rd",
  "qwerty",
  "letmein",
  "welcome",
  "admin",
  "changeme",
  "iloveyou",
  "123456789012",
];

export function passwordProblems(password: string, email?: string): string[] {
  const problems: string[] = [];
  if (password.length < MIN_PASSWORD_LENGTH) {
    problems.push(`Use at least ${MIN_PASSWORD_LENGTH} characters.`);
  }
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^a-zA-Z0-9]/].filter((re) => re.test(password));
  if (classes.length < 3) {
    problems.push("Mix at least three of: lowercase, uppercase, numbers and symbols.");
  }
  const lowered = password.toLowerCase();
  if (COMMON.some((word) => lowered.startsWith(word))) {
    problems.push("Avoid common passwords.");
  }
  const local = (email ?? "").split("@")[0]?.toLowerCase() ?? "";
  if (local.length >= 4 && lowered.includes(local)) {
    problems.push("Do not include your email name in the password.");
  }
  return problems;
}
