"""paperplot のテスト（pytest）。

生成ロジック（決定的な純関数）と Web の基本動作を検証する。
外部通信は行わない。サンプルは一般的な架空のテーマ。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as paperplot  # noqa: E402

SAMPLE = {
    "title": "地域の公共図書館における滞在型利用の実態",
    "background": "図書館の利用目的が貸出中心から滞在へ広がっている。",
    "rq": "滞在型利用者は図書館の何に価値を感じているのか",
    "claim": "座席の快適さより、人の気配と静けさの両立が価値の中心ではないか。",
    "prior": "佐藤（2020）貸出冊数の推移を分析。\n鈴木（2022）滞在行動を観察。",
    "target": "市立図書館Aの利用者30名",
    "method": "観察と半構造化インタビュー",
    "results": "滞在理由の最多は「静かだが一人ではない環境」だった。",
    "discussion": "仮説のうち静けさの要素は支持されたが、人の気配の効果は予想以上だった。",
    "significance": "滞在型サービスの設計指針に使える。",
}


def test_templates_present():
    assert set(paperplot.TEMPLATES) == {"standard", "review", "practice", "report"}
    for tpl in paperplot.TEMPLATES.values():
        assert tpl["name"]
        assert tpl["sections"]
        for heading, guide, keys in tpl["sections"]:
            assert heading and guide and keys
            for key in keys:
                assert key in paperplot.FIELD_LABELS


def test_outline_flows_inputs_standard():
    md = paperplot.build_outline("standard", SAMPLE)
    assert SAMPLE["title"] in md
    assert "## 1. 序論" in md
    assert SAMPLE["rq"] in md
    assert "佐藤（2020）貸出冊数の推移を分析。" in md
    assert SAMPLE["method"] in md
    assert SAMPLE["results"] in md
    assert SAMPLE["discussion"] in md
    # 先行研究メモの2行目は Markdown の継続行として欠けずに入る
    assert "\n  鈴木（2022）滞在行動を観察。" in md


def test_outline_each_template_has_all_sections():
    for key, tpl in paperplot.TEMPLATES.items():
        md = paperplot.build_outline(key, SAMPLE)
        for index, (heading, _guide, _keys) in enumerate(tpl["sections"], 1):
            assert "## %d. %s" % (index, heading) in md
        assert "この節で書くこと" in md
        assert tpl["name"] in md


def test_empty_inputs_do_not_break():
    md = paperplot.build_outline("standard", {})
    assert "（テーマ未入力）" in md
    assert "（未入力）" in md
    assert "## 1. 序論" in md
    # 全項目 None でも壊れない
    md2 = paperplot.build_outline("review", {k: None for k in paperplot.FIELD_LABELS})
    assert "（未入力）" in md2


def test_deterministic():
    first = paperplot.build_outline("practice", SAMPLE)
    second = paperplot.build_outline("practice", dict(SAMPLE))
    assert first == second


def test_unknown_template_falls_back():
    md = paperplot.build_outline("no-such-template", SAMPLE)
    assert paperplot.TEMPLATES["standard"]["name"] in md


def test_partially_filled():
    md = paperplot.build_outline("report", {"rq": "問いだけ先に決めた"})
    assert "問いだけ先に決めた" in md
    assert "（未入力）" in md  # ほかの項目はプレースホルダ


def _client():
    paperplot.app.config["TESTING"] = True
    return paperplot.app.test_client()


def test_web_get_shows_form():
    res = _client().get("/")
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "論文プロット" in body
    assert "研究問い" in body


def test_web_post_generates_outline():
    res = _client().post("/", data=dict(SAMPLE, template="standard"))
    assert res.status_code == 200
    body = res.get_data(as_text=True)
    assert "アウトライン" in body
    assert SAMPLE["title"] in body
    assert "ダウンロード" in body


def test_web_post_empty_form_ok():
    res = _client().post("/", data={"template": "review"})
    assert res.status_code == 200
    assert "（未入力）" in res.get_data(as_text=True)


def test_healthz():
    res = _client().get("/healthz")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}
