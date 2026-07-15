import pytest
from unittest.mock import AsyncMock, MagicMock

from app.engine.story_state import StoryStateManager
from app.persistence.world_store import WorldStore


# ----------------------------------------------------------------- initial / load
def test_initial_state_has_required_keys():
    mgr = StoryStateManager()
    s = mgr.initial_state()
    for key in ("act", "phase", "narrative_summary", "last_narration",
                "open_threads", "dramatic_tensions"):
        assert key in s
    assert s["act"] == 1
    assert s["phase"] == "setup"


def test_load_without_world_dir_returns_initial():
    mgr = StoryStateManager()
    s = mgr.load()
    assert s["phase"] == "setup"
    assert s["narrative_summary"] == ""


def test_load_missing_file_returns_initial(tmp_path):
    mgr = StoryStateManager(str(tmp_path))
    s = mgr.load()
    assert s == mgr.initial_state()


def test_load_merges_missing_keys(tmp_path):
    """老文件缺字段时，load 补齐默认键。"""
    store = WorldStore()
    # 故意写一个缺 phase / recent_narrations 的老文件
    store.save_story_state(str(tmp_path), {"act": 2, "narrative_summary": "x"})
    mgr = StoryStateManager(str(tmp_path))
    s = mgr.load()
    assert s["act"] == 2
    assert s["narrative_summary"] == "x"
    assert s["phase"] == "setup"           # 补齐
    assert s["recent_narrations"] == []    # 补齐


# ----------------------------------------------------------------- save / roundtrip
def test_save_then_load_roundtrip(tmp_path):
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    state["phase"] = "climax"
    state["narrative_summary"] = "艾伦与凯尔决战。"
    state["open_threads"].append({"description": "贝拉的下落", "intensity": 0.7})
    mgr.save(state)

    loaded = mgr.load()
    assert loaded["phase"] == "climax"
    assert loaded["narrative_summary"] == "艾伦与凯尔决战。"
    assert loaded["open_threads"][0]["description"] == "贝拉的下落"


def test_save_without_world_dir_is_noop(tmp_path):
    mgr = StoryStateManager()  # 无 world_dir
    mgr.save(mgr.initial_state())  # 不应抛异常
    # 无文件可查，load 仍返回 initial
    assert mgr.load() == mgr.initial_state()


def test_save_writes_yaml_file(tmp_path):
    mgr = StoryStateManager(str(tmp_path))
    mgr.save(mgr.initial_state())
    assert (tmp_path / "story_state.yaml").exists()


# ----------------------------------------------------------------- _tail
def test_tail_takes_last_sentences():
    mgr = StoryStateManager()
    narration = "第一句。第二句！第三句？第四句。"
    tail = mgr._tail(narration)
    # 默认保留最后 3 句
    assert tail == "第二句！第三句？第四句。"


def test_tail_short_text_returned_as_is():
    mgr = StoryStateManager()
    assert mgr._tail("只有一句。") == "只有一句。"


def test_tail_empty_returns_empty():
    mgr = StoryStateManager()
    assert mgr._tail("") == ""
    assert mgr._tail("   ") == ""


# ----------------------------------------------------------------- update_after_tick
def _mock_llm(summary: str = "压缩后的摘要。"):
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=summary)
    return llm


@pytest.mark.asyncio
async def test_update_sets_last_narration(tmp_path):
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    narration = "艾伦推门而入。风雪随之涌入。炉火颤了一下。"
    await mgr.update_after_tick(state, narration, tick=0, llm=_mock_llm())
    assert state["last_narration"]  # 非空
    assert state["last_narration"].endswith("炉火颤了一下。") or "炉火" in state["last_narration"]
    # tick 0 不触发摘要
    assert state["narrative_summary"] == ""
    # recent_narrations 滚动
    assert state["recent_narrations"] == [narration]


@pytest.mark.asyncio
async def test_update_no_summary_before_interval(tmp_path):
    """tick 0/1 不压缩摘要（仅 tick 2,5,8... 触发，因为 (tick+1)%3==0）。"""
    llm = _mock_llm()
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    await mgr.update_after_tick(state, "片段零。", tick=0, llm=llm)
    await mgr.update_after_tick(state, "片段一。", tick=1, llm=llm)
    assert llm.complete.await_count == 0  # 未到间隔，没调用 LLM
    assert state["narrative_summary"] == ""


@pytest.mark.asyncio
async def test_update_summary_at_interval(tmp_path):
    """tick=2 时 (2+1)%3==0 → 触发摘要压缩。"""
    llm = _mock_llm(summary="艾伦归来，酒馆对峙升级。")
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    state["recent_narrations"] = ["片段零。", "片段一。"]
    await mgr.update_after_tick(state, "片段二。", tick=2, llm=llm)
    assert llm.complete.await_count == 1
    assert state["narrative_summary"] == "艾伦归来，酒馆对峙升级。"


@pytest.mark.asyncio
async def test_update_llm_error_keeps_old_summary(tmp_path):
    """LLM 摘要失败时不阻塞、保留旧摘要。"""
    llm = MagicMock()
    llm.complete = AsyncMock(side_effect=Exception("LLM down"))
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    state["narrative_summary"] = "旧摘要。"
    state["recent_narrations"] = ["片段。"]
    # tick=2 触发摘要，但 LLM 失败
    out = await mgr.update_after_tick(state, "新片段。", tick=2, llm=llm)
    assert out["narrative_summary"] == "旧摘要。"  # 保留旧值
    # last_narration 仍更新
    assert out["last_narration"]


@pytest.mark.asyncio
async def test_update_persists_to_disk(tmp_path):
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    await mgr.update_after_tick(state, "一段叙述。", tick=0, llm=_mock_llm())
    loaded = WorldStore().load_story_state(str(tmp_path))
    assert loaded is not None
    assert loaded["last_narration"] == "一段叙述。"


@pytest.mark.asyncio
async def test_update_in_memory_no_persist():
    """无 world_dir 时 update 仍返回更新后的 state，但不落盘。"""
    mgr = StoryStateManager()
    state = mgr.initial_state()
    out = await mgr.update_after_tick(state, "叙述。", tick=0, llm=_mock_llm())
    assert out["last_narration"] == "叙述。"
    # recent_narrations 滚动
    assert out["recent_narrations"] == ["叙述。"]


@pytest.mark.asyncio
async def test_update_narration_window_capped(tmp_path):
    """recent_narrations 窗口上限为 6。"""
    mgr = StoryStateManager(str(tmp_path))
    state = mgr.initial_state()
    for i in range(10):
        await mgr.update_after_tick(state, f"片段{i}。", tick=i, llm=_mock_llm())
    assert len(state["recent_narrations"]) == 6
    assert state["recent_narrations"][0] == "片段4。"
    assert state["recent_narrations"][-1] == "片段9。"
