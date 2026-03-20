import os
from glob import glob

filepath = ".github/workflows/pr-requirements-enforce.yml"
with open(filepath, "r") as f:
    content = f.read()

# For pr-requirements-enforce.yml, it might have a slightly different structure. Let's check it.
print(content)
