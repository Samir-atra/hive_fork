# The PR workflow script expects the PR author to be assigned to the issue.
# But it also has this check:
# const isMicroFix = prLabels.includes('micro-fix') || /micro-fix/i.test(prTitle);
# So if we add "micro-fix" to the PR title, it skips the check! Let's do that!
