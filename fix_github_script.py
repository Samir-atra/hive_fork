import os, re

with open('.github/workflows/pr-requirements.yml', 'r') as f:
    text = f.read()
    print("Found pr-requirements.yml")
