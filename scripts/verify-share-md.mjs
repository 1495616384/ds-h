import fs from "node:fs";

const mdPath = process.argv[2] ?? "G:/ds-h/deepseek-share-r2pfqj5ctjatq899vp.md";
const t = fs.readFileSync(mdPath, "utf8");
const lines = t.split(/\r?\n/);
const fence = "```";

const count = (re) => lines.filter((l) => re.test(l)).length;

const report = {
  lines: lines.length,
  bytes: Buffer.byteLength(t),
  emptyBoldMarkers: count(/^\*{2,}$/),
  detailsOpen: count(/<details>/),
  detailsClose: count(/<\/details>/),
  fenceLines: count(/^```/),
  userHeaders: count(/^## \d+\. 👤/),
  assistantHeaders: count(/^## \d+\. 🤖/),
  messageHeaders: count(/^## \d+\. /),
  noContentPlaceholders: count(/（无内容）/),
  tocEntries: lines.slice(0, lines.findIndex((l) => l.trim() === "---")).filter((l) => /^\d+\. \[/.test(l)).length,
};

report.fencesBalanced = report.fenceLines % 2 === 0;
report.detailsBalanced = report.detailsOpen === report.detailsClose;
report.ok = report.emptyBoldMarkers === 0 && report.fencesBalanced && report.detailsBalanced
  && report.messageHeaders === report.userHeaders + report.assistantHeaders
  && report.tocEntries === report.messageHeaders;

console.log(JSON.stringify(report, null, 2));
process.exit(report.ok ? 0 : 1);
