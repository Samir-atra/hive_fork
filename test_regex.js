const title = "fix: update PR requirements workflow";
const body = `- Upgrade to \`actions/github-script@v8\` to fix Node.js deprecation warning.
- Check upstream \`adenhq/hive\` repository in \`pr-requirements.yml\` when issue isn't found locally.`;

const issuePattern = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)?\s*#(\d+)/gi;
const allText = `${title} ${body}`;
const matches = [...allText.matchAll(issuePattern)];
const issueNumbers = [...new Set(matches.map(m => parseInt(m[1], 10)))];

console.log("Found:", issueNumbers);
