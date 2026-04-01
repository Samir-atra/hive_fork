from framework.llm.router.task_classifier import TaskClassifier

def test_classify_coding():
    classifier = TaskClassifier()
    prompt = "Can you help me write a python script to parse this json?"
    assert classifier.classify(prompt) == "coding"

def test_classify_math_reasoning():
    classifier = TaskClassifier()
    prompt = "Please calculate the derivative of this equation."
    assert classifier.classify(prompt) == "math_reasoning"

def test_classify_function_calling():
    classifier = TaskClassifier()
    prompt = "Execute the fetch user api with this payload."
    assert classifier.classify(prompt) == "function_calling"

def test_classify_general():
    classifier = TaskClassifier()
    prompt = "What is the capital of France?"
    assert classifier.classify(prompt) == "general"

def test_classify_empty():
    classifier = TaskClassifier()
    assert classifier.classify("") == "general"
    assert classifier.classify(None) == "general"  # type: ignore

def test_classify_case_insensitive():
    classifier = TaskClassifier()
    prompt = "I need to deBuG this PyThOn fUnctIoN"
    assert classifier.classify(prompt) == "coding"

def test_classify_multimodal():
    classifier = TaskClassifier()
    prompt = [{"type": "text", "text": "Can you help me write a python script?"}, {"type": "image_url"}]
    assert classifier.classify(prompt) == "coding"
