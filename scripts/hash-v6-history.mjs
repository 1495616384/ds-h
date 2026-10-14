#!/usr/bin/env node
/** 历史冻结记录的实测 SHA-256（供 v6 信任文档登记，防止历史链被改写）。 */
import fs from "node:fs";
import crypto from "node:crypto";
const ROOT = "G:/ds-h";
const sha = (p) => crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex").toUpperCase();
for (const f of ["_xexp/H3-freeze-manifest.md", "_xexp/H3-freeze-manifest-v2.md",
                 "_xexp/H3-freeze-manifest-v3.md", "_xexp/H3-freeze-manifest-v4.md",
                 "_xexp/H3-freeze-manifest-v5.md"]) {
  console.log(`${sha(`${ROOT}/${f}`)}  ${f}`);
}
