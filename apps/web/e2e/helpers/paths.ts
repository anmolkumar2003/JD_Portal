import path from "node:path";

// Playwright always runs from apps/web (locally and in the e2e container, where it is /work),
// so cwd-based paths work whether the spec is loaded as CJS or ESM. `import.meta` does not.
const E2E_DIR = path.join(process.cwd(), "e2e");

export const FIXTURES_DIR = path.join(E2E_DIR, "fixtures");
/** Repo docs/ when the e2e container mounts it at /work/docs. */
export const DOCS_DIR = path.resolve(E2E_DIR, "..", "docs");
