with open("core/framework/utils/circuit_breaker.py", "r") as f:
    content = f.read()

if "import threading" not in content:
    content = "import threading\n" + content

with open("core/framework/utils/circuit_breaker.py", "w") as f:
    f.write(content)
