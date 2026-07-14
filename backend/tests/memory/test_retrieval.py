from app.memory.retrieval import MemoryRetriever
from app.models.memory import Memory

def _mem(content, importance=5, tick=0, embedding=None):
    return Memory(character_id="c1", world_id="w1", content=content, importance=float(importance), tick=tick, embedding=embedding or [])

def test_retrieve_returns_sorted_by_score():
    retriever = MemoryRetriever()
    memories = [
        _mem("贝拉三年前锻剑", importance=8, tick=1, embedding=[1,0]),
        _mem("今天下了雪", importance=3, tick=10, embedding=[0,1]),
        _mem("凯尔设局", importance=9, tick=2, embedding=[1,0]),
    ]
    results = retriever.retrieve(memories, query_vec=[1,0], current_tick=10, top_k=2)
    assert len(results) == 2
    # 高重要性 + 高相关性 应该排前面
    assert "凯尔" in results[0].content or "锻剑" in results[0].content

def test_retrieve_recency_boost():
    retriever = MemoryRetriever()
    old = _mem("很久以前的事", importance=5, tick=0)
    recent = _mem("刚发生的事", importance=5, tick=9)
    results = retriever.retrieve([old, recent], query_vec=[], current_tick=10, top_k=2)
    assert results[0].content == "刚发生的事"  # 近期优先

def test_retrieve_empty_memories():
    retriever = MemoryRetriever()
    results = retriever.retrieve([], query_vec=[1], current_tick=0, top_k=5)
    assert results == []

def test_retrieve_respects_top_k():
    retriever = MemoryRetriever()
    memories = [_mem(f"记忆{i}", importance=5, tick=i) for i in range(10)]
    results = retriever.retrieve(memories, query_vec=[], current_tick=10, top_k=3)
    assert len(results) == 3
