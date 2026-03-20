class MockUser:
    login = "VasuBansal7576"

class MockIssue:
    user = MockUser()

class MockResult:
    html_url = "https://github.com/adenhq/hive/issues/2579#issuecomment-123456"

class MockIssues:
    def get(self, issue_number):
        return MockIssue()
    def create_comment(self, issue_number, body):
        return MockResult()

class MockGhApi:
    issues = MockIssues()

api = MockGhApi()
issue_author = api.issues.get(2579).user.login
comment_body = f"""Hello @{issue_author}

I hope you are doing well,
I will start working on a PR, and please feel free to adapt and use my code in creating your pull request.

@RichardTang-Aden @bryanadenhq @TimothyZhang7

Please assign me to this issue, and I will create a pull request in a few minutes.

Kind regards
Samer"""
result = api.issues.create_comment(issue_number=2579, body=comment_body)
print(f"Comment posted: {result.html_url}")
