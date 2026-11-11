"""論文プロット（paperplot）

論文・レポートの「プロット」（構成・アウトライン）を組み立てる支援
ツール。論文タイプのテンプレートを選び、テーマ・研究問い・仮説・
方法・結果の要点などを項目別に入力すると、章・節の見出しに
「この節で書くこと」のガイド文を付けたアウトラインを Markdown で
生成する。創作用ツール plotbox の論文版。単一ファイル Flask。

構成（Unit）:
  Unit 1: 入力項目の定義
  Unit 2: 論文タイプ別テンプレートの定義
  Unit 3: アウトライン生成（決定的な純関数）
  Unit 4: 画面テンプレート
  Unit 5: ルート
"""
import os

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# ---------------------------------------------------------------
# Unit 1: 入力項目の定義
# (key, ラベル, 入力欄のヒント, 複数行かどうか)
# ---------------------------------------------------------------
FIELDS = [
    ("title", "テーマ・タイトル", "例：地域の公共図書館における滞在型利用の実態", False),
    ("background", "背景・問題意識", "なぜこのテーマを取り上げるのか、社会・学術の背景", True),
    ("rq", "研究問い（RQ）", "例：滞在型利用者は図書館の何に価値を感じているのか", False),
    ("claim", "仮説・主張", "問いに対する自分の予想・主張（まだ仮でよい）", True),
    ("prior", "先行研究メモ", "読んだ論文・資料と、その要点（1件ずつ改行）", True),
    ("target", "対象・データ", "調査対象、使うデータ、事例など", True),
    ("method", "方法", "調査・分析・開発の進め方", True),
    ("results", "結果の要点", "分かったこと・得られた成果（箇条書き可）", True),
    ("discussion", "考察で言いたいこと", "結果の解釈、予想との違い、意味づけ", True),
    ("significance", "意義・貢献", "この研究が何の役に立つか、新しさはどこか", True),
]
FIELD_LABELS = {key: label for key, label, _hint, _multi in FIELDS}

# ---------------------------------------------------------------
# Unit 2: 論文タイプ別テンプレートの定義
# sections: (見出し, ガイド文, 流し込む入力項目の key リスト)
# ---------------------------------------------------------------
TEMPLATES = {
    "standard": {
        "name": "卒業論文（標準型）",
        "description": "序論→先行研究→方法→結果→考察→結論の王道の流れ。実証系の卒論に。",
        "sections": [
            ("序論",
             "背景から問題を絞り込み、研究問いと仮説を提示する。「なぜこの研究をするのか」に答える章。",
             ["background", "rq", "claim"]),
            ("先行研究",
             "問いに関わる先行研究を整理し、まだ明らかになっていないこと（ギャップ）を明確にする。自分の研究の位置づけを書く。",
             ["prior"]),
            ("方法",
             "対象とデータ、調査・分析の手順を、他の人が再現できる具体さで書く。",
             ["target", "method"]),
            ("結果",
             "方法で得られた事実だけを、解釈を混ぜずに提示する。図表の読み取り結果もここ。",
             ["results"]),
            ("考察",
             "結果を解釈し、仮説と照らし合わせる。先行研究との一致・相違と、その理由を論じる。",
             ["discussion", "significance"]),
            ("結論",
             "研究問いへの答えを短く述べ、研究の意義と今後の課題（残された問題）で締める。",
             ["rq", "results"]),
        ],
    },
    "review": {
        "name": "比較・整理型（先行研究の比較が中心）",
        "description": "複数の先行研究を比較・整理し、論点と自分の立場を示すタイプ。文献研究や卒論の整理型に。",
        "sections": [
            ("序論",
             "テーマの背景と、なぜ今これらの研究を比較する必要があるのかを述べ、研究問いを提示する。",
             ["background", "rq"]),
            ("先行研究の整理",
             "取り上げる研究を、対象・方法・結論の観点で1件ずつ要約する。後の比較の土台。",
             ["prior"]),
            ("比較・対照",
             "比較軸（対象／方法／結論の違い）をそろえて並べ、共通点と対立点を抜き出す。表にすると読みやすい。",
             ["claim"]),
            ("論点と自分の立場",
             "比較から浮かぶ論点を示し、それに対する自分の立場・主張と根拠を述べる。",
             ["discussion", "claim"]),
            ("結論",
             "研究問いへの答えと、比較を通じて見えた今後の課題をまとめる。",
             ["rq", "discussion"]),
        ],
    },
    "practice": {
        "name": "実践・開発報告型",
        "description": "授業実践、開発、フィールドワークなど「やってみた」報告が中心のタイプ。",
        "sections": [
            ("序論（背景と目的）",
             "取り組む課題の背景と、実践・開発の目的を述べる。何を解決・検証したいのかを明確に。",
             ["background", "rq"]),
            ("先行研究・関連事例",
             "似た実践や先行する開発事例を挙げ、自分の取り組みとの違い（新しさ）を示す。",
             ["prior"]),
            ("実践・開発の内容",
             "対象と実施内容を時系列や手順で具体的に書く。工夫した点は理由とセットで。",
             ["target", "method"]),
            ("結果・評価",
             "実施結果と、評価指標や参加者の反応など、効果を測った事実を提示する。",
             ["results"]),
            ("考察",
             "うまくいった点・いかなかった点とその理由を分析し、改善案につなげる。",
             ["discussion", "significance"]),
            ("結論",
             "目的に対する達成度をまとめ、今後の課題と展望を述べる。",
             ["results", "discussion"]),
        ],
    },
    "report": {
        "name": "レポート型",
        "description": "授業レポートや短い報告向けの軽量版。はじめに→本論→考察→おわりに。",
        "sections": [
            ("はじめに",
             "テーマを取り上げる理由と、このレポートで述べる問い・主張の予告を書く。",
             ["background", "rq"]),
            ("本論",
             "主張を支える根拠（資料・データ・事例）を、理由の強い順に並べて述べる。",
             ["claim", "prior", "results"]),
            ("考察",
             "根拠から言えること、反対の見方への応答、自分の解釈を述べる。",
             ["discussion"]),
            ("おわりに",
             "主張を再確認し、残る疑問や調べ足りなかった点を正直に書いて締める。",
             ["claim", "significance"]),
        ],
    },
}
DEFAULT_TEMPLATE = "standard"


# ---------------------------------------------------------------
# Unit 3: アウトライン生成
# 同じ入力には必ず同じ出力を返す（決定的）。
# ---------------------------------------------------------------
def _clean(value):
    """入力値を整える（前後の空白除去、空なら空文字）。"""
    if value is None:
        return ""
    return str(value).strip()


def _field_block(key, inputs):
    """1項目分の Markdown 行を作る。未入力ならプレースホルダ。"""
    label = FIELD_LABELS.get(key, key)
    value = _clean(inputs.get(key))
    if not value:
        return "- **%s**：（未入力）" % label
    lines = value.splitlines()
    block = ["- **%s**：%s" % (label, lines[0])]
    for extra in lines[1:]:
        block.append("  %s" % extra)
    return "\n".join(block)


def build_outline(template_key, inputs):
    """テンプレートと入力からアウトラインの Markdown を生成する。"""
    template = TEMPLATES.get(template_key) or TEMPLATES[DEFAULT_TEMPLATE]
    inputs = inputs or {}
    title = _clean(inputs.get("title")) or "（テーマ未入力）"
    out = []
    out.append("# 『%s』アウトライン" % title)
    out.append("")
    out.append("- 論文タイプ：%s" % template["name"])
    out.append("- 生成：paperplot（論文プロット）")
    out.append("")
    for index, (heading, guide, keys) in enumerate(template["sections"], 1):
        out.append("## %d. %s" % (index, heading))
        out.append("")
        out.append("> この節で書くこと：%s" % guide)
        out.append("")
        for key in keys:
            out.append(_field_block(key, inputs))
        out.append("")
    out.append("---")
    out.append("メモ：各節の「（未入力）」は、これから調べ・考える項目の目印です。")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------
# Unit 4: 画面テンプレート
# ---------------------------------------------------------------
PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>論文プロット（paperplot）</title>
<style>
*{box-sizing:border-box}
body{font-family:sans-serif;max-width:760px;margin:2em auto;padding:0 1em;
color:#222;background:#fff;line-height:1.6}
h1{font-size:1.5em}
h2{font-size:1.15em;margin-top:1.6em}
label{display:block;font-weight:bold;margin:1em 0 .3em}
.hint{font-weight:normal;color:#666;font-size:.88em}
input[type=text],textarea,select{width:100%;padding:.55em;font-size:1em;
border:1px solid #bbb;border-radius:8px;background:#fff;color:#222}
textarea{min-height:4.5em}
.bigbtn{display:inline-block;font-size:1.1em;padding:.7em 1.6em;margin:1em 0;
background:#2e6da4;color:#fff;border:none;border-radius:8px;cursor:pointer}
.bigbtn:hover{background:#245a89}
.subbtn{padding:.45em 1em;margin-right:.5em;background:#eee;color:#222;
border:1px solid #bbb;border-radius:8px;cursor:pointer;font-size:.95em}
.result{width:100%;min-height:22em;font-family:monospace;font-size:.9em}
footer{margin-top:2em;color:#777;font-size:.85em}
@media (prefers-color-scheme: dark){
  body{background:#1c1e22;color:#e8e8e8}
  input[type=text],textarea,select{background:#2a2d33;color:#e8e8e8;border-color:#555}
  .hint{color:#aaa}
  .subbtn{background:#2a2d33;color:#e8e8e8;border-color:#555}
  footer{color:#999}
}
</style>
</head><body>
<h1>📝 論文プロット</h1>
<p>論文・レポートの構成（アウトライン）を組み立てる道具です。論文タイプを選び、分かる項目だけ入力して「アウトラインを作る」を押してください。空の項目は「これから書くこと」の目印として残ります。</p>
<form method="post" action="/">
  <label for="template">論文タイプ</label>
  <select id="template" name="template">
    {% for key, tpl in templates.items() %}
    <option value="{{ key }}" {% if key == selected %}selected{% endif %}>
      {{ tpl.name }} ― {{ tpl.description }}</option>
    {% endfor %}
  </select>
  {% for key, label, hint, multi in fields %}
  <label for="f_{{ key }}">{{ label }}
    <span class="hint">{{ hint }}</span></label>
  {% if multi %}
  <textarea id="f_{{ key }}" name="{{ key }}">{{ values.get(key, '') }}</textarea>
  {% else %}
  <input type="text" id="f_{{ key }}" name="{{ key }}"
         value="{{ values.get(key, '') }}">
  {% endif %}
  {% endfor %}
  <button type="submit" class="bigbtn">🧩 アウトラインを作る</button>
</form>
{% if outline %}
<h2>生成されたアウトライン（Markdown）</h2>
<p>
  <button type="button" class="subbtn" id="copyBtn">📋 コピー</button>
  <button type="button" class="subbtn" id="dlBtn">⬇ ダウンロード</button>
</p>
<textarea class="result" id="outline" readonly>{{ outline }}</textarea>
<script>
document.getElementById("copyBtn").addEventListener("click", function(){
  var ta = document.getElementById("outline");
  ta.select();
  if (navigator.clipboard) { navigator.clipboard.writeText(ta.value); }
  else { document.execCommand("copy"); }
});
document.getElementById("dlBtn").addEventListener("click", function(){
  var text = document.getElementById("outline").value;
  var blob = new Blob([text], {type: "text/markdown"});
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "paperplot-outline.md";
  a.click();
  URL.revokeObjectURL(a.href);
});
</script>
{% endif %}
<footer>paperplot ― 創作用ツール plotbox の論文版です。入力内容はサーバーに保存されません。</footer>
</body></html>
"""


# ---------------------------------------------------------------
# Unit 5: ルート
# ---------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    values = {}
    outline = None
    selected = DEFAULT_TEMPLATE
    if request.method == "POST":
        selected = request.form.get("template", DEFAULT_TEMPLATE)
        if selected not in TEMPLATES:
            selected = DEFAULT_TEMPLATE
        for key, _label, _hint, _multi in FIELDS:
            values[key] = request.form.get(key, "")
        outline = build_outline(selected, values)
    return render_template_string(
        PAGE,
        templates=TEMPLATES,
        fields=FIELDS,
        values=values,
        selected=selected,
        outline=outline,
    )


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
