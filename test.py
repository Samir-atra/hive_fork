with open(".github/workflows/pr-requirements.yml", "r") as f:
    print("actions/github-script@v8" in f.read())
