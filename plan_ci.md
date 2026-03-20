1. **Research**
   - The CI failure indicates that `actions/github-script@v7` is deprecated as it runs on Node.js 20. It needs to be updated to `actions/github-script@v8`.
   - The CI failure also indicates `PR must reference an issue` failure at line 197 of `.github/workflows/pr-requirements.yml` because the workflow fails to find the issue context in the fork.
   - We need to modify the GitHub Actions workflow script to gracefully check the upstream `adenhq/hive` repository if the issue isn't found in the local context.

2. **Core Logic**
   - Update `actions/github-script@v7` to `actions/github-script@v8` in all `.github/workflows/*.yml` files where present.
   - Edit `.github/workflows/pr-requirements.yml`:
     - Modify the issue resolution logic in the `actions/github-script` to try getting the issue from `context.repo.owner` and `context.repo.repo`.
     - If that fails (e.g. 404), fallback to getting the issue from `owner: 'adenhq'` and `repo: 'hive'`.

3. **Validation**
   - Verify the syntax of the modified `.yml` files.

4. **Documentation**
   - No explicit documentation changes required beyond the commit message.
