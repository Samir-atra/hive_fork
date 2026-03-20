import re

with open(".github/workflows/pr-requirements-backfill.yml", "r") as f:
    content = f.read()

# Replace the issue fetching logic
search = """              for (const issueNum of issueNumbers) {
                try {
                  const { data: issue } = await github.rest.issues.get({
                    owner: context.repo.owner,
                    repo: context.repo.repo,
                    issue_number: issueNum,
                  });"""

replace = """              for (const issueNum of issueNumbers) {
                try {
                  // Determine whether to check upstream or fork repo
                  let targetOwner = context.repo.owner;
                  let targetRepo = context.repo.repo;

                  try {
                    // Check fork first
                    const { data: issue } = await github.rest.issues.get({
                      owner: context.repo.owner,
                      repo: context.repo.repo,
                      issue_number: issueNum,
                    });
                    targetOwner = context.repo.owner;
                    targetRepo = context.repo.repo;
                  } catch(err) {
                    // Fallback to upstream if fork check fails
                    console.log(`Issue #${issueNum} not found in fork, checking upstream adenhq/hive...`);
                    targetOwner = 'adenhq';
                    targetRepo = 'hive';
                  }

                  const { data: issue } = await github.rest.issues.get({
                    owner: targetOwner,
                    repo: targetRepo,
                    issue_number: issueNum,
                  });"""

content = content.replace(search, replace)

with open(".github/workflows/pr-requirements-backfill.yml", "w") as f:
    f.write(content)
