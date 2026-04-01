with open("core/framework/llm/router/task_classifier.py", "r") as f:
    content = f.read()

# Add handling for list in task classifier
content = content.replace('def classify(self, prompt: str) -> str:', 'def classify(self, prompt: str | list) -> str:')

import_block = "import re\n"
new_import = "import re\nfrom typing import Union, List, Dict, Any\n"
if new_import not in content:
    content = content.replace(import_block, new_import)

classify_method = '''    def classify(self, prompt: str) -> str:
        """Classifies the prompt into a task category based on regex patterns.

        Args:
            prompt: The input prompt string to classify.

        Returns:
            The matched category name or 'general' if none match.
        """
        if not prompt:
            return "general"

        for category, pattern in self.patterns.items():
            if pattern.search(prompt):
                return category

        return "general"'''

new_classify = '''    def classify(self, prompt: Union[str, List[Dict[str, Any]]]) -> str:
        """Classifies the prompt into a task category based on regex patterns.

        Args:
            prompt: The input prompt string or list of dicts to classify.

        Returns:
            The matched category name or 'general' if none match.
        """
        if not prompt:
            return "general"

        text_prompt = ""
        if isinstance(prompt, list):
            # Extract text from multimodal prompt
            text_parts = []
            for item in prompt:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            text_prompt = " ".join(text_parts)
        elif isinstance(prompt, str):
            text_prompt = prompt
        else:
            text_prompt = str(prompt)

        for category, pattern in self.patterns.items():
            if pattern.search(text_prompt):
                return category

        return "general"'''
content = content.replace(classify_method, new_classify)

with open("core/framework/llm/router/task_classifier.py", "w") as f:
    f.write(content)
