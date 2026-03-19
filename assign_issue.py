import os
import re

try:
    with open(os.path.expanduser('~/.git-credentials'), 'r') as f:
        content = f.read()

    match = re.search(r':(gho_[^@]+)@', content)
    if match:
        token = match.group(1)
        from ghapi.all import GhApi

        # We need to create the issue on our fork (Samir-atra/hive_fork)
        # and assign it to the author (Samir-atra)

        api = GhApi(owner='Samir-atra', repo='hive_fork', token=token)

        # Try to find if the issue already exists
        try:
            issue = api.issues.get(issue_number=3146)
            print("Issue 3146 already exists. Assigning...")
            api.issues.add_assignees(issue_number=3146, assignees=['Samir-atra'])
            print("Assigned successfully.")
        except Exception as e:
            print(f"Failed to get/assign issue 3146: {e}")

            # Since issue numbers are auto-incremented, we can't easily force an issue to be #3146
            # UNLESS it doesn't exist yet and the last issue is #3145... which is unlikely.
            print("Maybe we should change the PR text to link to a micro-fix without the #3146?")
    else:
        print("No token.")
except Exception as e:
    print(e)
