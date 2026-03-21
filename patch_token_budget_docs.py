with open("core/framework/graph/token_budget.py", "r") as f:
    text = f.read()

target = '    """Exception raised when execution exceeds the configured token budget."""'

replacement = '''    """Exception raised when execution exceeds the configured token budget.

    Attributes:
        budget (int): The maximum allowed tokens.
        current (int): The total accumulated tokens that exceeded the budget.
        node_id (str | None): The ID of the node being executed when the limit was exceeded.
    """'''

text = text.replace(target, replacement)

with open("core/framework/graph/token_budget.py", "w") as f:
    f.write(text)
