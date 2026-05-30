import fs from 'node:fs';

const manifest = JSON.parse(fs.readFileSync('audit/original-screenshots-manifest.json', 'utf8'));

let output = '# InfluenceIQ Phase 1 Screenshot Index\n\n';
output += 'Generated from `audit/original-screenshots-manifest.json`.\n\n';
output += '| Route | Source | Width | Captured Size | File |\n';
output += '|---|---|---:|---:|---|\n';

for (const screenshot of manifest.screenshots) {
  output += `| ${screenshot.slug} | \`${screenshot.file}\` | ${screenshot.width} | ${screenshot.pageWidth}x${screenshot.pageHeight} | \`audit/original-screenshots/${screenshot.filename}\` |\n`;
}

fs.writeFileSync('audit/screenshot-index.md', output);
