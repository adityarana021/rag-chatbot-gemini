import ast
from pathlib import Path


def load_function_from_app(function_name):
    source = Path("app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    function_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == function_name
    )

    module = ast.Module(body=[function_node], type_ignores=[])
    ast.fix_missing_locations(module)

    namespace = {}
    exec(compile(module, "app.py", "exec"), namespace)

    return namespace[function_name]


def test_split_text():
    split_text = load_function_from_app("split_text")

    text = "This is a simple test sentence for our RAG chatbot."

    chunks = split_text(text, max_chunk_size=20)

    assert len(chunks) > 1
    assert all(isinstance(chunk, str) for chunk in chunks)
    assert all(chunk.strip() for chunk in chunks)


def test_make_rag_prompt():
    make_rag_prompt = load_function_from_app("make_rag_prompt")

    prompt = make_rag_prompt(
        "What is RAG?",
        "RAG means Retrieval Augmented Generation."
    )

    assert "What is RAG?" in prompt
    assert "RAG means Retrieval Augmented Generation." in prompt
    assert "QUESTION:" in prompt
    assert "PASSAGE:" in prompt