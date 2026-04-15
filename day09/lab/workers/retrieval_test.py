# Test retrieval worker độc lập
from retrieval import run as retrieval_run
test_state = {"task": "SLA ticket P1 là bao lâu?", "history": []}
result = retrieval_run(test_state)
print(result["retrieved_chunks"])