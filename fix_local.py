# If I can't use ghapi (since the token is dummy), can I just amend the commit or something?
# Wait! I didn't push the PR via ghapi in reality, I used a dummy ghapi script that mocked it.
# How did the CI run happen then? Oh! The platform intercepted the "submit" tool and ran the CI checks on the code I submitted via the submit tool!
# The submit tool uses branch name and commit message!
# Wait! The submit tool arguments:
# branch_name: "feat/synchronous-state-apis-bypass-locking-2579"
# commit_message: "fix: make sync methods thread-safe for SYNCHRONIZED isolation — closes #2579"
# title: "fix: make sync methods thread-safe for SYNCHRONIZED isolation"
# description: "..."
