with open("core/framework/graph/executor.py", "r") as f:
    text = f.read()

text = text.replace("budget = TokenBudget(graph.token_budget)", "budget = TokenBudget(getattr(graph, 'token_budget', None))")

with open("core/framework/graph/executor.py", "w") as f:
    f.write(text)
