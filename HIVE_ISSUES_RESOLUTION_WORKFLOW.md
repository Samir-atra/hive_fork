# Hive Issue Resolution Capability List

## Issue Resolution Workflow
To ensure high-quality and consistent contributions, follow this standardized workflow for every issue:

1.  **Analyze**: Thoroughly check the issue description and comments on the issue to understand requirements, edge cases, and architectural alignment.
2.  **If accept for work -> comment**
    - comment on the issue that you accept for work and that you will start working on it, and need to be assigned to the issue.
2.  **Branching Strategy**: 
    - Reset the new branch to the upstream main branch of the hive repository.
    - Create a new git branch utilizing the issue title and number as the identifier (e.g., `feat/issue-title-####`).
    - **Important**: Each branch must contain ONLY the commits relevant to the specific issue being resolved. Do not include commits from other issues or unrelated changes. If you accidentally include unrelated commits, reset the branch to upstream/main and cherry-pick only the relevant commit(s).
3.  **Implementation Planning**:
    - Generate a detailed work plan covering:
        - **Core Logic**: The primary code changes required.
        - **Validation**: Strategic unit tests (stored in the corresponding `tests` directory).
        - **Documentation**: Updates to READMEs or markdown guides within the repository.
4.  **Double check**:
    - Double check that all the relevant files in the core directory and the rest of the repository are updated with the new modifications and additions thatwere made to resolve the issue.
4.  **Commit & Push**: Execute `git add`, `git commit` with a descriptive message including the code files and the test files and documentation edited for this issue resolution and excluding the secrets files, and `git push` to your fork.
5.  **Pull Request (PR)**:
    - Create a pull request description markdown file.
    - Use `github-mcp-server` to generate a PR on the `adenhq/hive` repository.
    - Ensure the PR title is relevant and the description comprehensively details the changes, explicitly mentioning that it `Resolves #<IssueNumber>`.
