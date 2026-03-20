with open("core/framework/storage/checkpoint_store.py", "r") as f:
    content = f.read()

content = content.replace(
    'checkpoints = [cp for cp in checkpoints if getattr(cp, "is_starred", False) == is_starred]',
    'checkpoints = [\n                cp for cp in checkpoints if getattr(cp, "is_starred", False) == is_starred\n            ]'
)

with open("core/framework/storage/checkpoint_store.py", "w") as f:
    f.write(content)
