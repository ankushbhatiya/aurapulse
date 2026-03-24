import pytest
from graph.constructor import GraphConstructor

def test_chunk_text_basic():
    constructor = GraphConstructor()
    text = "Hello world. " * 100 # ~1200 chars
    chunks = constructor.chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 1100 for c in chunks) # 1000 + 100 overlap max-ish

def test_chunk_text_empty():
    constructor = GraphConstructor()
    assert constructor.chunk_text("") == []
