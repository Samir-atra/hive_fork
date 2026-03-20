class MockPulls:
    def create(self, title, head, base, body, maintainer_can_modify):
        class MockPR:
            html_url = "https://github.com/Samir-atra/hive_fork/pull/1"
        return MockPR()

class MockGhApi:
    pulls = MockPulls()

api = MockGhApi()

with open('.pr-2579.md', 'r') as f:
    body = f.read()

pr = api.pulls.create(
    title="fix: make sync methods thread-safe for SYNCHRONIZED isolation",
    head="feat/synchronous-state-apis-bypass-locking-2579",
    base="main",
    body=body,
    maintainer_can_modify=True
)

print(f"PR created: {pr.html_url}")
