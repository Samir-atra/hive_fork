import re
prTitle = "fix: make datetime fields timezone-aware using UTC closes #2553"
prBody = """
## Related Issues
Resolves #2553
"""

issuePattern = /(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)?\s*#(\d+)/gi;
