"""bot/hit_log.py 单元测试(10 单元:env 默认 + env 启用 + env 路径 + 关闭/启用 record + append 多次 + now_event 必填 + 可选归一 + 写失败不抛 + get_default_hitlog)"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from bot.hit_log import HitLog, HitLogConfig, get_default_hitlog


def test_env_disabled_by_default():
    """env 默认关闭(避免本地 dev 被噪声淹没)。"""
    with patch.dict(os.environ, {}, clear=True):
        cfg = HitLogConfig.from_env()
    assert cfg.enabled is False
    # Path 解析时 ./ 前缀会被规范化(PosixPath 不保留 ./),比较 Path 对象
    assert cfg.path == Path("data/bot_hit_log.jsonl")


def test_env_enabled_via_one():
    with patch.dict(os.environ, {"FEISHU_BOT_HIT_LOG_ENABLED": "1"}, clear=True):
        cfg = HitLogConfig.from_env()
    assert cfg.enabled is True


def test_env_path_override():
    with patch.dict(os.environ, {"FEISHU_BOT_HIT_LOG_PATH": "/tmp/custom_hit.jsonl"}, clear=True):
        cfg = HitLogConfig.from_env()
    # PosixPath 会去掉 /tmp 前缀里多余的部分,直接比较 Path 对象
    assert cfg.path == Path("/tmp/custom_hit.jsonl")


def test_env_disabled_accepts_common_falsy():
    """常见假值(0/false/no/空)都被识别为关闭。"""
    for v in ("0", "", "false", "False", "FALSE", "no", "No"):
        with patch.dict(os.environ, {"FEISHU_BOT_HIT_LOG_ENABLED": v}, clear=True):
            cfg = HitLogConfig.from_env()
        assert cfg.enabled is False, f"value={v!r} should be disabled"


def test_disabled_record_returns_false():
    """关闭时 record 返回 False 且不写盘。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "log.jsonl"
        cfg = HitLogConfig(enabled=False, path=path)
        log = HitLog(cfg)
        assert log.record({"text": "x"}) is False
        assert not path.exists()


def test_enabled_record_writes_jsonl():
    """启用时 record 写 1 行 JSONL,字段可 round-trip。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "log.jsonl"
        cfg = HitLogConfig(enabled=True, path=path)
        log = HitLog(cfg)
        assert log.record({"text": "button", "ok": True}) is True
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["text"] == "button"
        assert obj["ok"] is True


def test_multiple_records_append():
    """多次 record 追加多行(append-only 语义)。"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "log.jsonl"
        cfg = HitLogConfig(enabled=True, path=path)
        log = HitLog(cfg)
        log.record({"text": "a", "ok": True})
        log.record({"text": "b", "ok": False})
        log.record({"text": "c", "ok": True})
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        assert [json.loads(l)["text"] for l in lines] == ["a", "b", "c"]


def test_now_event_minimal_required_fields():
    """now_event 必填字段映射正确,可选字段默认值。"""
    cfg = HitLogConfig(enabled=False, path=Path("/tmp/x"))
    log = HitLog(cfg)
    ev = log.now_event(
        chat_id="oc_x", sender="ou_y", text="button", ok=True, note="hit=5"
    )
    assert ev["chat_id"] == "oc_x"
    assert ev["sender"] == "ou_y"
    assert ev["text"] == "button"
    assert ev["ok"] is True
    assert ev["note"] == "hit=5"
    assert ev["echo"] == ""
    assert ev["reply_len"] == 0
    assert ev["dry_run"] is True
    assert ev["event_type"] == ""
    assert "ts" in ev and ev["ts"].endswith("+08:00")


def test_now_event_normalizes_none_optionals():
    """chat_id / sender / event_type 传 None 时归一为 ""(便于 JSONL 一致性)。"""
    cfg = HitLogConfig(enabled=False, path=Path("/tmp/x"))
    log = HitLog(cfg)
    ev = log.now_event(
        chat_id=None, sender=None, text="help", ok=True, note="cmd=help"
    )
    assert ev["chat_id"] == ""
    assert ev["sender"] == ""
    assert ev["event_type"] == ""


def test_record_returns_false_on_write_error(monkeypatch, tmp_path):
    """写盘抛异常时 record 返回 False 不阻塞主流程(Path.open 走 io.open,monkeypatch io.open)。"""
    path = tmp_path / "log.jsonl"
    cfg = HitLogConfig(enabled=True, path=path)
    log = HitLog(cfg)

    def boom(*a, **kw):
        raise IOError("disk full simulated")

    # Path.open 在 Python 3.10+ 走 io.open(不是 builtins.open)
    import io
    monkeypatch.setattr(io, "open", boom)
    assert log.record({"text": "x"}) is False


def test_get_default_hitlog_returns_hitlog_instance():
    log1 = get_default_hitlog()
    log2 = get_default_hitlog()
    assert isinstance(log1, HitLog)
    assert isinstance(log2, HitLog)
    assert type(log1) is type(log2)


def test_record_creates_parent_dir(tmp_path):
    """父目录不存在时自动 mkdir -p。"""
    nested = tmp_path / "deep" / "nested" / "log.jsonl"
    cfg = HitLogConfig(enabled=True, path=nested)
    log = HitLog(cfg)
    assert log.record({"text": "x"}) is True
    assert nested.exists()
    assert json.loads(nested.read_text(encoding="utf-8").strip())["text"] == "x"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
