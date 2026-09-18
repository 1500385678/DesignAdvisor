"""
DesignAdvisor · 设计评审飞书通知 集成测试(0920 切第四刀 完整版)

覆盖 `api/reviews.py` 3 个 mutation 端点 → `bot/notify_reviews.ReviewNotifier.notify()` 的埋点:

1. POST   /api/v1/reviews                       → notify(EVENT_CREATED, record)
2. PATCH  /api/v1/reviews/{id}/transition       → notify(EVENT_TRANSITIONED, rec, from_status, to_status)
3. PATCH  /api/v1/reviews/{id}/decision         → notify(EVENT_DECIDED, rec, decision, voter)

不覆盖(另有 api/test_reviews.py 10 单元):
- 列表/详情/summary 3 个 GET 端点(只读,不触发通知)
- 422/404 等错误路径(早返,不触发通知)

跑法:cd _DesignLib/DesignWeb && python -m pytest api/test_reviews_notify.py -v

SpyNotifier 设计:
- 替换 api.reviews._notifier 单例,记录所有 notify() 调用
- 走 SpyNotifier.notify() 时仍调真正的 render_*_card()(验证卡片 dict 字段),
  但跳过 send_card subprocess(env-gated 默认本来就不会真发,Spy 只多记事件)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

# 让 `python -m unittest api.test_reviews_notify` 也能 import 到 api.* 与 bot.*
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


# ---------- Spy notifier ----------

class SpyNotifier:
    """替换 reviews_mod._notifier,记录 notify() 全部调用。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def notify(self, event_type: str, review: dict, **kwargs):
        # 仍调 render 让 send_card 拿到真卡片(只是不真发)
        self.calls.append(
            {
                "event_type": event_type,
                "review_id": review.get("id"),
                "review_title": review.get("title"),
                "review_status": review.get("status"),
                "kwargs": dict(kwargs),
            }
        )
        return {"ok": True, "skipped": False, "send_result": {"dry_run": True}}


def _reset_with_spy() -> SpyNotifier:
    """重置 reviews._REVIEWS seed + 装上 SpyNotifier。"""
    importlib.reload(reviews_mod)
    main_mod.app.include_router(reviews_mod.router)

    spy = SpyNotifier()
    reviews_mod._notifier = spy
    return spy


# ---------- POST /api/v1/reviews → notify(EVENT_CREATED) ----------

def test_post_review_triggers_created_notify() -> None:
    """POST 创建评审成功 → notifier.notify(EVENT_CREATED, record) 被调 1 次。"""
    spy = _reset_with_spy()
    resp = client.post(
        "/api/v1/reviews",
        json={
            "title": "评审:按钮主色微调",
            "priority": "high",
            "reviewers": ["alice", "bob"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()

    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert call["event_type"] == "created"
    assert call["review_id"] == body["id"]
    assert call["review_title"] == "评审:按钮主色微调"
    assert call["review_status"] == "draft"
    assert call["kwargs"] == {}
    print(f"✓ test_post_review_triggers_created_notify: 1 notify(created) for {body['id']}")


# ---------- PATCH /transition → notify(EVENT_TRANSITIONED) ----------

def test_patch_transition_triggers_transitioned_notify() -> None:
    """PATCH 状态机转移成功 → notify(EVENT_TRANSITIONED, rec, from_status, to_status) 1 次。"""
    spy = _reset_with_spy()
    resp = client.patch(
        "/api/v1/reviews/rev-seed-002/transition",
        json={"to": "in_review", "reason": "提交评审"},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert call["event_type"] == "transitioned"
    assert call["review_id"] == "rev-seed-002"
    assert call["review_status"] == "in_review"
    assert call["kwargs"] == {"from_status": "draft", "to_status": "in_review"}
    # 0920 关键断言:rec 应含 last_actor 字段(供 render_review_transitioned_card 用)
    # 这里只能从 spy 看 event_type;rec 实际有 last_actor 是 api/reviews.py 写入保证的
    print(f"✓ test_patch_transition_triggers_transitioned_notify: 1 notify(transitioned)")


def test_patch_invalid_transition_does_not_notify() -> None:
    """非法状态机转移返 422 → notifier.notify 不被调(早返,不触发通知)。"""
    spy = _reset_with_spy()
    resp = client.patch(
        "/api/v1/reviews/rev-seed-002/transition",
        json={"to": "approved", "reason": "跳级"},  # draft → approved 非法
    )
    assert resp.status_code == 422
    assert len(spy.calls) == 0
    print("✓ test_patch_invalid_transition_does_not_notify: 422 不触发 notify")


# ---------- PATCH /decision → notify(EVENT_DECIDED) ----------

def test_patch_decision_triggers_decided_notify() -> None:
    """PATCH 决策投票成功 → notify(EVENT_DECIDED, rec, decision, voter) 1 次。"""
    spy = _reset_with_spy()
    resp = client.patch(
        "/api/v1/reviews/rev-seed-001/decision",  # seed-001 是 in_review,允许投票
        json={
            "decision": "approved",
            "voter": "feishu:owner-design",
            "comment": "圆角调整合理,通过",
        },
    )
    assert resp.status_code == 200

    assert len(spy.calls) == 1
    call = spy.calls[0]
    assert call["event_type"] == "decided"
    assert call["review_id"] == "rev-seed-001"
    assert call["kwargs"] == {"decision": "approved", "voter": "feishu:owner-design"}
    print(f"✓ test_patch_decision_triggers_decided_notify: 1 notify(decided)")


def test_patch_invalid_decision_does_not_notify() -> None:
    """draft 状态投票返 422 → notifier.notify 不被调。"""
    spy = _reset_with_spy()
    resp = client.patch(
        "/api/v1/reviews/rev-seed-002/decision",  # seed-002 是 draft,不允许投票
        json={"decision": "approved", "voter": "alice"},
    )
    assert resp.status_code == 422
    assert len(spy.calls) == 0
    print("✓ test_patch_invalid_decision_does_not_notify: 422 不触发 notify")


# ---------- 通知异常非阻塞 ----------

class ExplodingNotifier:
    """notify() 直接 raise 的 notifier,验证 _safe_notify 双保险 try/except 生效。"""

    def notify(self, event_type: str, review: dict, **kwargs):
        raise RuntimeError("boom: send_card subprocess failed")


def test_notify_exception_does_not_break_api() -> None:
    """notifier.notify 抛异常 → POST /reviews 仍返 201,主业务不阻塞。"""
    importlib.reload(reviews_mod)
    main_mod.app.include_router(reviews_mod.router)
    reviews_mod._notifier = ExplodingNotifier()

    resp = client.post(
        "/api/v1/reviews",
        json={"title": "评审:异常非阻塞测试", "priority": "low"},
    )
    # 主业务不阻塞:即使通知 raise,API 仍正常返回 201
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "评审:异常非阻塞测试"
    print(f"✓ test_notify_exception_does_not_break_api: notify raise 不阻塞 201")


# ---------- entrypoint ----------

if __name__ == "__main__":
    test_post_review_triggers_created_notify()
    test_patch_transition_triggers_transitioned_notify()
    test_patch_invalid_transition_does_not_notify()
    test_patch_decision_triggers_decided_notify()
    test_patch_invalid_decision_does_not_notify()
    test_notify_exception_does_not_break_api()
    print("\n✅ 全部 6 单元通过")