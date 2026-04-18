import { execFileSync } from "node:child_process";
import { rmSync } from "node:fs";
import path from "node:path";

const root = process.cwd();
const buildDir = path.join(root, ".test-dist");
const testFiles = [
  path.join(root, ".test-dist", "src", "components", "__tests__", "dashboard.test.js"),
  path.join(root, ".test-dist", "src", "components", "__tests__", "dashboard-api.test.js"),
];

rmSync(buildDir, { force: true, recursive: true });

try {
  if (process.platform === "win32") {
    execFileSync(
      "cmd.exe",
      ["/c", "node_modules\\.bin\\tsc.cmd", "-p", "tsconfig.test.json"],
      { stdio: "inherit", cwd: root }
    );
  } else {
    execFileSync(path.join(root, "node_modules", ".bin", "tsc"), ["-p", "tsconfig.test.json"], {
      stdio: "inherit",
      cwd: root,
    });
  }
  for (const testFile of testFiles) {
    execFileSync(process.execPath, [testFile], { stdio: "inherit" });
  }
} finally {
  rmSync(buildDir, { force: true, recursive: true });
}
