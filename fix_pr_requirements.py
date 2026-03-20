import os
from glob import glob

for filepath in glob(".github/workflows/*.yml"):
    with open(filepath, "r") as f:
        content = f.read()

    # The memory instruction says:
    # "The CI workflow's PR requirement check verifies if the PR author is assigned to the linked issue. When modifying these scripts, ensure they gracefully fallback to checking the upstream `adenhq/hive` repository, as issues referenced in fork PRs will not exist in the fork's local context."

    # We replace:
    # owner: context.repo.owner,
    # repo: context.repo.repo,
    # issue_number: issueNum,
    # with a try-except block that tries adenhq/hive if it fails.

    if "check-requirements" in filepath or "pr-requirements.yml" in filepath or "pr-requirements-enforce.yml" in filepath:
        if "const { data: issue } = await github.rest.issues.get({" in content:
            # We need to change how the issue is fetched.
            content = content.replace(
"""            for (const issueNum of issueNumbers) {
              try {
                const { data: issue } = await github.rest.issues.get({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  issue_number: issueNum,
                });""",
"""            for (const issueNum of issueNumbers) {
              try {
                let issue;
                try {
                  const res = await github.rest.issues.get({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    issue_number: issueNum,
                  });
                  issue = res.data;
                } catch (err) {
                  console.log(`  Issue #${issueNum} not found in ${context.repo.owner}/${context.repo.repo}, falling back to adenhq/hive`);
                  const res = await github.rest.issues.get({
                    owner: 'adenhq',
                    repo: 'hive',
                    issue_number: issueNum,
                  });
                  issue = res.data;
                }""")

            with open(filepath, "w") as f:
                f.write(content)
