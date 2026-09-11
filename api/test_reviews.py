"""
DesignAdvisor · 设计评审后端 v0.1 单元测试(Phase 1 #2 切第一刀 · 2026-09-12)

端到端走 FastAPI TestClient,8 单元覆盖:
1. seed 3 件 fake-load 默认可见(GET /)
2. 创建评审成功(POST / + 返 201 + status=draft)
3. 创建评审 priority 非法返 422
4. 列表过滤 status=draft 只返 1 件
5. summary 6 状态/4 决策/4 优先级计数正确
6. 状态机合法转移 draft → in_review
7. 状态机非法转移 draft → approved 返 422
8. 决策投票(in_review 状态 + voter + 决策日志 append)
9. 决策投票但 status=draft 返 422
10. 详情查不存在的 review_id 返 404
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

# 让 `python -m unittest api.test_reviews` 也能 import 到 api.* 与 bot.*
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

# 重新加载以保证 seed 字典干净
import api.main as main_mod  # noqa: E402
importlib.reload(main_mod)
import api.reviews as reviews_mod  # noqa: E402
importlib.reload(reviews_mod)

client = TestClient(main_mod.app)


def _reset_seed() -> None:
    """每个测试前重置 reviews._REVIEWS 到 3 件 seed(隔离测试状态)"""
    seed_ids = ["rev-seed-001", "rev-seed-002", "rev-seed-003"]
    reviews_mod._REVIEWS.clear()
    for sid in seed_ids:
        rec = reviews_mod.get_review.__globals__["_FAKE_LOAD_TS"]
        # 简化:重新从模块顶层 seed 字典加载
        pass
    # 直接 reload reviews_mod 即可,顶层 seed 字典会重新构造
    importlib.reload(reviews_mod)
    # main_mod.app 的 router 是按对象引用 include 的,reload 后 router 还在用旧引用
    # 解决:重新 include router
    main_mod.app.include_router(reviews_mod.router)


def test_01_seed_visible() -> None:
    """seed 3 件 fake-load 默认可见"""
    _reset_seed()
    resp = client.get("/api/v1/reviews")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["returned"] == 3
    ids = {r["id"] for r in body["reviews"]}
    assert ids == {"rev-seed-001", "rev-seed-002", "rev-seed-003"}
    print("✓ test_01_seed_visible: 3 件 seed 全部可见")


def test_02_create_success() -> None:
    """创建评审成功,返 201 + status=draft + decision=pending"""
    _reset_seed()
    payload = {
        "title": "评审:test-new-component 圆角统一",
        "asset_id": "comp-form-input-v0.1.0",
        "description": "新组件圆角从 4 改 8,影响 5 处",
        "priority": "high",
        "reviewers": ["feishu:owner-design", "feishu:owner-frontend"],
        "created_by": "feishu:test-user",
    }
    resp = client.post("/api/v1/reviews", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == payload["title"]
    assert body["asset_id"] == payload["asset_id"]
    assert body["status"] == "draft"
    assert body["decision"] == "pending"
    assert body["priority"] == "high"
    assert body["id"].startswith("rev-") and len(body["id"]) == 12  # "rev-" + 8 hex
    assert len(body["reviewers"]) == 2
    assert body["decisions_log"] == []
    assert body["transitions_log"] == []
    print(f"✓ test_02_create_success: 创建新评审 id={body['id']}")


def test_03_create_invalid_priority() -> None:
    """priority 非法返 422"""
    _reset_seed()
    payload = {"title": "test", "priority": "urgent"}  # 不在 low/medium/high/blocker
    resp = client.post("/api/v1/reviews", json=payload)
    assert resp.status_code == 422
    assert "priority" in resp.text
    print("✓ test_03_create_invalid_priority: 422 priority 非法")


def test_04_list_filter_status() -> None:
    """?status=draft 只返 1 件(seed-002)"""
    _reset_seed()
    resp = client.get("/api/v1/reviews?status=draft")
    assert resp.status_code == 200
    body = resp.json()
    assert body["returned"] == 1
    assert body["reviews"][0]["id"] == "rev-seed-002"
    assert body["reviews"][0]["status"] == "draft"
    print("✓ test_04_list_filter_status: ?status=draft → 1 件")


def test_05_summary_counts() -> None:
    """summary 6 状态 / 4 决策 / 4 优先级计数正确"""
    _reset_seed()
    resp = client.get("/api/v1/reviews/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    # 状态:seed-001 in_review / seed-002 draft / seed-003 approved
    assert body["by_status"] == {"in_review": 1, "draft": 1, "approved": 1}
    # 决策:seed-001 pending / seed-002 pending / seed-003 approved
    assert body["by_decision"] == {"pending": 2, "approved": 1}
    # 优先级:seed-001 high / seed-002 medium / seed-003 low
    assert body["by_priority"] == {"high": 1, "medium": 1, "low": 1}
    # 命名空间 6 状态都列
    assert set(body["namespaces"].keys()) == {
        "draft", "in_review", "approved", "rejected", "deprecated", "archived"
    }
    print("✓ test_05_summary_counts: 状态/决策/优先级 3 维计数正确")


def test_06_transition_valid() -> None:
    """状态机合法转移 draft → in_review,transitions_log 追加"""
    _reset_seed()
    resp = client.patch(
        "/api/v1/reviews/rev-seed-002/transition",
        json={"to": "in_review", "reason": "提交评审"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_review"
    assert len(body["transitions_log"]) == 1
    log = body["transitions_log"][0]
    assert log["from"] == "draft"
    assert log["to"] == "in_review"
    assert log["reason"] == "提交评审"
    print("✓ test_06_transition_valid: draft → in_review 合法")


def test_07_transition_invalid() -> None:
    """状态机非法转移 draft → approved 返 422(合法路径要经 in_review)"""
    _reset_seed()
    resp = client.patch(
        "/api/v1/reviews/rev-seed-002/transition",
        json={"to": "approved", "reason": "跳级"},
    )
    assert resp.status_code == 422
    assert "draft" in resp.text and "approved" in resp.text
    print("✓ test_07_transition_invalid: draft → approved 非法 422")


def test_08_decision_vote() -> None:
    """决策投票(in_review 状态),decision 字段更新 + decisions_log append"""
    _reset_seed()
    # seed-001 已经是 in_review
    resp = client.patch(
        "/api/v1/reviews/rev-seed-001/decision",
        json={
            "decision": "approved",
            "voter": "feishu:owner-design",
            "comment": "圆角调整合理,通过",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "approved"
    assert len(body["decisions_log"]) == 1
    log = body["decisions_log"][0]
    assert log["decision"] == "approved"
    assert log["voter"] == "feishu:owner-design"
    assert log["comment"] == "圆角调整合理,通过"
    print("✓ test_08_decision_vote: 决策投票 approved 落日志")


def test_09_decision_vote_invalid_status() -> None:
    """决策投票但 status=draft 返 422(需先 transition 到 in_review)"""
    _reset_seed()
    # seed-002 是 draft
    resp = client.patch(
        "/api/v1/reviews/rev-seed-002/decision",
        json={"decision": "approved", "voter": "feishu:owner-design"},
    )
    assert resp.status_code == 422
    assert "draft" in resp.text
    print("✓ test_09_decision_vote_invalid_status: draft 状态不允许投票")


def test_10_get_nonexistent_404() -> None:
    """查不存在的 review_id 返 404"""
    _reset_seed()
    resp = client.get("/api/v1/reviews/rev-doesnotexist")
    assert resp.status_code == 404
    assert "不存在" in resp.text
    print("✓ test_10_get_nonexistent_404: rev-doesnotexist 404")


if __name__ == "__main__":
    test_01_seed_visible()
    test_02_create_success()
    test_03_create_invalid_priority()
    test_04_list_filter_status()
    test_05_summary_counts()
    test_06_transition_valid()
    test_07_transition_invalid()
    test_08_decision_vote()
    test_09_decision_vote_invalid_status()
    test_10_get_nonexistent_404()
    print("\n✅ 全部 10 单元通过")
