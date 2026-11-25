import path from "node:path";
import { fileURLToPath } from "node:url";

/** ESM-safe paths for Playwright (package.json has "type": "module"). */
const E2E_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export const FIXTURES_DIR = path.join(E2E_DIR, "fixtures");
/** Repo docs/ when the e2e container mounts it at /work/docs. */
export const DOCS_DIR = path.resolve(E2E_DIR, "..", "docs");
