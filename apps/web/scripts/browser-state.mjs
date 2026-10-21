// Which browser state is this machine in? Prints INSTALLED, MISSING or UNRESOLVABLE -- one line, no exit code,
// so the caller can name the remedy it means.
//
// Why a file and not a `node -e` inside the shell script: Node resolves a bare specifier from the importing
// file's directory, so living beside the instruments makes this probe answer the same question they will. Run as a
// one-liner it resolved from wherever the caller's cwd happened to be -- and in CI's `ci` job, which installs
// `apps/web` and `apps/vscode` but never a root `node_modules`, that turned a resolution failure into a false
// "chromium is not installed" refusal. Three causes, three answers: the gate that refuses for the wrong reason gets
// deleted instead of fixed.
import { existsSync } from "node:fs";

try {
  const { chromium } = await import("playwright");
  console.log(existsSync(chromium.executablePath()) ? "INSTALLED" : "MISSING");
} catch {
  console.log("UNRESOLVABLE");
}
