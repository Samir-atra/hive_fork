const issuePattern = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)?\s*#(\d+)/gi;
console.log("matches: ", "feat: Add manual checkpoints (starring) support - closes #6613".match(issuePattern));
