import re
with open('core/framework/graph/safe_eval.py', 'r') as f:
    code = f.read()

has_constant = 'def visit_Constant' in code
print(f"Has visit_Constant: {has_constant}")
