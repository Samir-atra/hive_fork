The CI check `check-requirements` failed because the issue number could not be found by the GitHub action.
Looking at my last `submit` tool payload:

```
description: ## Description

This PR implements the Cost Feedback feature for developers running agents locally. When a developer executes an agent via the CLI (`hive run` or `hive shell`), the output will now include a real-time, detailed cost breakdown detailing total cost, costs by individual steps, and costs by the specific models used.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [x] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Related Issues

Resolves #2505
```

The script extracts the issue numbers via regex:
`const issuePattern = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)?\s*#(\d+)/gi;`

Ah! My description uses `Resolves #2505`. This should have matched. Let's see what PR #60 has as title and description.
Wait, the `submit` tool overwrites the PR if we use the same branch name, but the `submit` tool implementation in the framework updates the PR with the new title and description. If it didn't update it, the issue might be that I used a different branch name initially, or the submit tool just didn't overwrite the description.
Wait, let's just make the PR title `feat: output cost feedback to CLI - closes #2505`. The regex checks both title and body: `const allText = ${prTitle} ${prBody};`.
If I put `closes #2505` in the title, it will definitely match.

Let me just do that!
