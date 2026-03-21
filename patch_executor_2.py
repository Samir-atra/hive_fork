with open("core/framework/graph/executor.py", "r") as f:
    text = f.read()

text = text.replace("steps_executed=steps_executed", "steps_executed=steps")
text = text.replace("total_latency=total_latency,", "total_latency_ms=total_latency,")

with open("core/framework/graph/executor.py", "w") as f:
    f.write(text)
