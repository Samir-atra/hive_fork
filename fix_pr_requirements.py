import re
import os

files = [
    ".github/workflows/link-discord.yml",
    ".github/workflows/pr-requirements-backfill.yml",
    ".github/workflows/pr-requirements.yml",
    ".github/workflows/pr-check-command.yml",
    ".github/workflows/pr-requirements-enforce.yml"
]

for file in files:
    if os.path.exists(file):
        with open(file, 'r') as f:
            content = f.read()

        # update action to v8
        content = content.replace("uses: actions/github-script@v7", "uses: actions/github-script@v8")

        if file == ".github/workflows/pr-requirements.yml":
            # the issue requires that we gracefully fallback to checking adenhq/hive repository
            # Let's replace the loop checking context.repo.owner/repo with a fallback

            old_loop = """            for (const issueNum of issueNumbers) {
              try {
                const { data: issue } = await github.rest.issues.get({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  issue_number: issueNum,
                });

                const assigneeLogins = (issue.assignees || []).map(a => a.login);
                if (assigneeLogins.includes(prAuthor)) {
                  issueWithAuthorAssigned = issueNum;
                  console.log(`  Issue #${issueNum} has PR author ${prAuthor} as assignee`);
                  break;
                } else {
                  issuesWithoutAuthor.push({
                    number: issueNum,
                    assignees: assigneeLogins
                  });
                  console.log(`  Issue #${issueNum} assignees: ${assigneeLogins.length > 0 ? assigneeLogins.join(', ') : 'none'} (PR author: ${prAuthor})`);
                }
              } catch (error) {
                console.log(`  Issue #${issueNum} not found or inaccessible`);
              }
            }"""

            new_loop = """            for (const issueNum of issueNumbers) {
              try {
                let issueOwner = context.repo.owner;
                let issueRepo = context.repo.repo;
                let issue;

                try {
                  const { data } = await github.rest.issues.get({
                    owner: issueOwner,
                    repo: issueRepo,
                    issue_number: issueNum,
                  });
                  issue = data;
                } catch (err) {
                  console.log(`  Issue #${issueNum} not found in ${issueOwner}/${issueRepo}, falling back to adenhq/hive`);
                  const { data } = await github.rest.issues.get({
                    owner: 'adenhq',
                    repo: 'hive',
                    issue_number: issueNum,
                  });
                  issue = data;
                }

                const assigneeLogins = (issue.assignees || []).map(a => a.login);
                if (assigneeLogins.includes(prAuthor)) {
                  issueWithAuthorAssigned = issueNum;
                  console.log(`  Issue #${issueNum} has PR author ${prAuthor} as assignee`);
                  break;
                } else {
                  issuesWithoutAuthor.push({
                    number: issueNum,
                    assignees: assigneeLogins
                  });
                  console.log(`  Issue #${issueNum} assignees: ${assigneeLogins.length > 0 ? assigneeLogins.join(', ') : 'none'} (PR author: ${prAuthor})`);
                }
              } catch (error) {
                console.log(`  Issue #${issueNum} not found or inaccessible`);
              }
            }"""

            content = content.replace(old_loop, new_loop)

        with open(file, 'w') as f:
            f.write(content)
