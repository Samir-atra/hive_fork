## Description
This PR introduces the Email Assistant Agent integration as a new template in the Hive framework. It implements an end-to-end email workflow incorporating intent classification, automated response generation, and predefined workflow execution, aligned with the proposal in #4188.

### Features
- Fetch logic to retrieve unread emails.
- Intent classification using `classify-intent` node.
- Automated generation of replies with `generate-reply` node.
- Workflow execution routing via `execute-workflow` node.
- Comprehensive reporting node to log all actions.

Resolves #4188.
