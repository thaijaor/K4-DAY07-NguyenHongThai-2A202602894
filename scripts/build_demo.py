"""Sinh demo.html tu ket qua benchmark — trang trinh chieu offline cho buoi demo.

Doc so lieu tu ket_qua_benchmark.txt (embedder that) va
ket_qua_benchmark_mock.txt (MockEmbedder), khong go tay so nao.

    python scripts/build_demo.py

Mo demo.html bang trinh duyet. Trang tu chua, khong can mang.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent

# So lieu cua hai thanh vien con lai, lay tu ket_qua_benchmark.txt trong repo
# nop cua ho (deu chay MockEmbedder, cung corpus, cung 5 query).
TEAM = [
    {"ten": "Trần Mạnh Tùng", "chien_luoc": "HeadingChunker(600)",
     "chunk": 107, "dai_tb": 448, "diem": 1,
     "manh": "Chunk trùng khít một điều khoản",
     "yeu": "Chunk to, các mục trong cùng tài liệu điểm gần bằng nhau"},
    {"ten": "Nguyễn Hồng Thái", "chien_luoc": "FixedSizeChunker(300, 50)",
     "chunk": 199, "dai_tb": 294, "diem": 2,
     "manh": "Duy nhất có overlap — không mất thông tin ở mép cắt",
     "yeu": "Cắt giữa câu, chunk có thể mở đầu bằng từ cụt", "toi": True},
    {"ten": "Nguyễn Mạnh Cường", "chien_luoc": "RecursiveChunker(300)",
     "chunk": 210, "dai_tb": 215, "diem": 1,
     "manh": "Bám ranh giới tự nhiên, chunk gọn và đều",
     "yeu": "Chunk vụn nhất; không overlap"},
]

# Do bang compute_similarity() voi gemini-embedding-001.
CAP_CAU = [
    ("Tôi muốn trả lại đơn hàng bị lỗi.",
     "Làm sao để yêu cầu hoàn tiền cho sản phẩm hỏng?", "cao", 0.8482),
    ("Người mua yêu cầu trả hàng hoàn tiền.",
     "Người bán xử lý đơn trả hàng hoàn tiền.", "cao", 0.8600),
    ("Thời hạn yêu cầu đổi trả là bao nhiêu ngày?",
     "Phí vận chuyển nội thành là bao nhiêu?", "thấp", 0.6042),
    ("Đóng gói hàng hoàn trả bằng vật liệu chống sốc.",
     "Quy định về hàng hóa cấm vận chuyển trên sàn.", "thấp", 0.6256),
    ("Đơn hàng đã được giao thành công.",
     "Đơn hàng giao không thành công.", "cao", 0.8379),
]


def parse_run(path: Path) -> dict:
    """Bóc số liệu từ một file ket_qua_benchmark."""
    text = path.read_text(encoding="utf-8")
    run = {
        "embedder": _one(r"^Mô hình nhúng \(Embedder\): (.+)$", text),
        "chunks": int(_one(r"Vector Store: (\d+) chunks", text) or 0),
        "tong": int(_one(r"RETRIEVAL QUALITY\): (\d+) /", text) or 0),
        "queries": [],
        "ab": {"khong_loc": [], "co_loc": []},
    }

    for block in re.split(r"^-{80}$", text, flags=re.M):
        m = re.search(r"^Query (\d+): (.+)$", block, re.M)
        if not m:
            continue
        diem = _one(r"Điểm đánh giá câu này: (\d)/2", block)
        top3 = [
            {"doc": d, "score": float(sc), "preview": pv.strip()}
            for sc, d, pv in re.findall(
                r"\[\d\] Score: ([-\d.]+) \| Doc: (\S+) \| Preview: (.+)", block)
        ]
        run["queries"].append({
            "id": int(m.group(1)),
            "cau_hoi": m.group(2).strip(),
            "gold": _one(r"^Câu trả lời chuẩn \(Gold\): (.+)$", block) or "",
            "loc": _one(r"^Metadata filter áp dụng: (.+)$", block),
            "diem": int(diem or 0),
            "top3": top3,
        })

    ab = re.search(r"THỬ NGHIỆM A/B(.+?)(?:\n={80}|\Z)", text, re.S)
    if ab:
        phan = re.split(r"^\d\. Khi (?:KHÔNG dùng|CÓ) filter", ab.group(1), flags=re.M)
        for key, chunk in zip(("khong_loc", "co_loc"), phan[1:3]):
            run["ab"][key] = [
                {"doc": d, "audience": a}
                for d, a in re.findall(r"Doc: (\S+) \(audience: (\w+)\)", chunk)
            ]
    return run


def _one(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else None


def e(value) -> str:
    return html.escape(str(value), quote=True)


def bar(value: int, total: int, kind: str) -> str:
    pct = round(value / total * 100) if total else 0
    return (f'<div class="bar" role="img" aria-label="{value} trên {total}">'
            f'<div class="bar-fill {kind}" style="width:{pct}%"></div></div>')


def build(real: dict, mock: dict) -> str:
    delta = real["tong"] - mock["tong"]

    # Ket qua dung san: dung khi khong goi duoc demo_server.py
    dung_san = json.dumps([
        {
            "cau_hoi": q["cau_hoi"],
            "loc": q["loc"],
            "top": [{"doc_id": t["doc"], "score": t["score"], "content": t["preview"]}
                    for t in q["top3"]],
        }
        for q in real["queries"]
    ], ensure_ascii=False)

    # --- Bang 5 query, doi chieu mock vs that
    hang_query = []
    for q_real, q_mock in zip(real["queries"], mock["queries"]):
        top1 = q_real["top3"][0] if q_real["top3"] else {"doc": "—", "score": 0}
        loc = (f'<span class="chip chip-filter">{e(q_real["loc"])}</span>'
               if q_real["loc"] else "")
        hang_query.append(f"""
        <tr>
          <td class="num">{q_real['id']}</td>
          <td>
            <p class="q">{e(q_real['cau_hoi'])}</p>
            <p class="gold"><span class="lbl">Gold</span> {e(q_real['gold'])}</p>
            {loc}
          </td>
          <td><span class="score {_klass(q_mock['diem'])}">{q_mock['diem']}/2</span></td>
          <td>
            <span class="score {_klass(q_real['diem'])}">{q_real['diem']}/2</span>
            <p class="doc">{e(top1['doc'])} · <span class="mono">{top1['score']:.3f}</span></p>
          </td>
        </tr>""")

    # --- A/B filter (lay tren ban mock, noi khac biet ro nhat)
    def ab_col(rows, title, note):
        items = "".join(
            f'<li><span class="aud aud-{e(r["audience"])}">{e(r["audience"])}</span>'
            f'<span class="mono doc-id">{e(r["doc"])}</span></li>'
            for r in rows) or "<li>—</li>"
        return (f'<div class="ab-col"><h4>{title}</h4>'
                f'<ol class="ab-list">{items}</ol><p class="note">{note}</p></div>')

    ab_html = (
        ab_col(mock["ab"]["khong_loc"], "Không lọc",
               "Cả 3 kết quả đều là tài liệu người mua — trả lời sai đối tượng.")
        + ab_col(mock["ab"]["co_loc"], 'Lọc <code>audience = seller</code>',
                 "Chuyển hẳn sang tài liệu người bán.")
    )

    # --- Bang 3 thanh vien
    hang_team = []
    for m in TEAM:
        toi = " hang-toi" if m.get("toi") else ""
        dau = '<span class="chip chip-me">chiến lược của tôi</span>' if m.get("toi") else ""
        hang_team.append(f"""
        <tr class="{toi.strip()}">
          <td><strong>{e(m['ten'])}</strong> {dau}<p class="mono strat">{e(m['chien_luoc'])}</p></td>
          <td class="num mono">{m['chunk']}</td>
          <td class="num mono">{m['dai_tb']}</td>
          <td class="num"><span class="score {_klass(m['diem'], 10)}">{m['diem']}/10</span></td>
          <td class="pros"><span class="plus">+</span> {e(m['manh'])}<br>
              <span class="minus">−</span> {e(m['yeu'])}</td>
        </tr>""")

    # --- 5 cap cau
    hang_cap = []
    for i, (a, b, du_doan, diem) in enumerate(CAP_CAU, 1):
        muc = "cao" if diem >= 0.70 else "thấp"
        hang_cap.append(f"""
        <tr>
          <td class="num">{i}</td>
          <td>{e(a)}</td>
          <td>{e(b)}</td>
          <td class="num">{du_doan}</td>
          <td class="num mono"><strong>{diem:.4f}</strong></td>
          <td class="num">{'✓' if muc == du_doan else '✗'}</td>
        </tr>""")

    return f"""<title>Truy xuất chính sách Shopee</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;800&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
  :root {{
    --ground: #f4f5f3;
    --surface: #ffffff;
    --ink: #191d1c;
    --ink-soft: #5a635f;
    --line: #dcdfda;
    --accent: #1f4f45;
    --accent-soft: #e3ece9;
    --good: #2c6e52;
    --good-soft: #dfeee6;
    --warn: #9a5a21;
    --warn-soft: #f6e9db;
    --dim: #8a918c;
    --shadow: 0 1px 2px rgba(25, 29, 28, .06);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --ground: #131614;
      --surface: #1b201d;
      --ink: #eef1ee;
      --ink-soft: #a8b1ab;
      --line: #2c332e;
      --accent: #7fc4b0;
      --accent-soft: #1f2b27;
      --good: #6dbd96;
      --good-soft: #1b2a22;
      --warn: #d69a5e;
      --warn-soft: #2b2218;
      --dim: #79827c;
      --shadow: none;
    }}
  }}
  :root[data-theme="dark"] {{
    --ground: #131614;
    --surface: #1b201d;
    --ink: #eef1ee;
    --ink-soft: #a8b1ab;
    --line: #2c332e;
    --accent: #7fc4b0;
    --accent-soft: #1f2b27;
    --good: #6dbd96;
    --good-soft: #1b2a22;
    --warn: #d69a5e;
    --warn-soft: #2b2218;
    --dim: #79827c;
    --shadow: none;
  }}

  body {{
    background: var(--ground);
    color: var(--ink);
    font-family: "Be Vietnam Pro", system-ui, -apple-system, sans-serif;
    font-size: 15px;
    line-height: 1.55;
  }}
  .mono {{ font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, monospace;
           font-variant-numeric: tabular-nums; }}
  .wrap {{ max-width: 1080px; margin-inline: auto; padding-inline: 20px;
           padding-block: 40px 72px; display: flex; flex-direction: column; gap: 48px; }}

  header h1 {{ font-size: clamp(28px, 4.5vw, 42px); font-weight: 800; line-height: 1.12;
               letter-spacing: -.02em; margin: 0 0 10px; text-wrap: balance; }}
  .eyebrow {{ font-size: 12px; font-weight: 600; letter-spacing: .12em;
              text-transform: uppercase; color: var(--accent); margin: 0 0 14px; }}
  .sub {{ color: var(--ink-soft); margin: 0; max-width: 62ch; }}

  section {{ display: flex; flex-direction: column; gap: 18px; }}
  h2 {{ font-size: 20px; font-weight: 600; letter-spacing: -.01em; margin: 0;
        padding-bottom: 10px; border-bottom: 2px solid var(--line); }}
  h2 .n {{ color: var(--dim); font-weight: 500; margin-right: 10px; }}
  .lede {{ margin: 0; color: var(--ink-soft); max-width: 68ch; }}

  /* Luan diem chinh */
  .thesis {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .big {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
          padding: 22px 24px; box-shadow: var(--shadow); }}
  .big .cap {{ font-size: 12px; font-weight: 600; letter-spacing: .08em;
               text-transform: uppercase; color: var(--ink-soft); margin: 0 0 6px; }}
  .big .val {{ font-size: clamp(38px, 7vw, 56px); font-weight: 800; line-height: 1;
               letter-spacing: -.03em; margin: 0 0 4px; }}
  .big.is-mock .val {{ color: var(--warn); }}
  .big.is-real .val {{ color: var(--good); }}
  .big .engine {{ margin: 0 0 14px; color: var(--ink-soft); font-size: 13px; }}
  .bar {{ height: 8px; border-radius: 99px; background: var(--line); overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 99px; }}
  .bar-fill.warn {{ background: var(--warn); }}
  .bar-fill.good {{ background: var(--good); }}
  .callout {{ background: var(--accent-soft); border-left: 3px solid var(--accent);
              border-radius: 0 8px 8px 0; padding: 14px 18px; margin: 0; }}
  .callout strong {{ color: var(--ink); }}

  .scroll {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--surface);
           border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
  th {{ text-align: left; font-size: 11px; font-weight: 600; letter-spacing: .09em;
        text-transform: uppercase; color: var(--ink-soft); padding: 12px 14px;
        border-bottom: 1px solid var(--line); white-space: nowrap; }}
  td {{ padding: 13px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num, th.num {{ text-align: center; white-space: nowrap; }}
  .hang-toi {{ background: var(--accent-soft); }}
  .strat {{ margin: 3px 0 0; font-size: 12px; color: var(--ink-soft); }}
  .pros {{ font-size: 13px; color: var(--ink-soft); line-height: 1.5; }}
  .plus {{ color: var(--good); font-weight: 600; }}
  .minus {{ color: var(--warn); font-weight: 600; }}
  .q {{ margin: 0 0 5px; font-weight: 500; }}
  .gold {{ margin: 0; font-size: 13px; color: var(--ink-soft); }}
  .lbl {{ font-size: 10px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
          color: var(--dim); margin-right: 5px; }}
  .doc {{ margin: 5px 0 0; font-size: 11px; color: var(--ink-soft); }}
  .score {{ display: inline-block; min-width: 46px; padding: 3px 9px; border-radius: 6px;
            font-weight: 600; font-size: 13px;
            font-family: "JetBrains Mono", ui-monospace, monospace; }}
  .s-good {{ background: var(--good-soft); color: var(--good); }}
  .s-mid {{ background: var(--warn-soft); color: var(--warn); }}
  .s-bad {{ background: var(--line); color: var(--ink-soft); }}
  .chip {{ display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 99px;
           font-weight: 500; }}
  .chip-filter {{ background: var(--accent-soft); color: var(--accent);
                  font-family: "JetBrains Mono", monospace; margin-top: 7px; }}
  .chip-me {{ background: var(--accent); color: var(--surface); }}

  .ab {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  .ab-col {{ background: var(--surface); border: 1px solid var(--line);
             border-radius: 10px; padding: 18px 20px; box-shadow: var(--shadow); }}
  .ab-col h4 {{ margin: 0 0 12px; font-size: 14px; font-weight: 600; }}
  .ab-col code {{ font-family: "JetBrains Mono", monospace; font-size: 12px;
                  background: var(--accent-soft); color: var(--accent);
                  padding: 1px 5px; border-radius: 4px; }}
  .ab-list {{ margin: 0 0 12px; padding-left: 20px; display: flex;
              flex-direction: column; gap: 9px; }}
  .ab-list li {{ font-size: 13px; }}
  .aud {{ display: inline-block; font-size: 10px; font-weight: 600; text-transform: uppercase;
          letter-spacing: .05em; padding: 1px 7px; border-radius: 4px; margin-right: 8px; }}
  .aud-buyer {{ background: var(--warn-soft); color: var(--warn); }}
  .aud-seller {{ background: var(--good-soft); color: var(--good); }}
  .aud-both {{ background: var(--line); color: var(--ink-soft); }}
  .doc-id {{ font-size: 12px; }}
  .note {{ margin: 0; font-size: 12px; color: var(--ink-soft); }}

  footer {{ border-top: 1px solid var(--line); padding-top: 18px;
            font-size: 12px; color: var(--dim); }}
  footer p {{ margin: 0 0 4px; }}


  /* --- Hoi thu --- */
  .ask {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px;
          padding: 20px; box-shadow: var(--shadow); display: flex;
          flex-direction: column; gap: 14px; }}
  .status {{ display: flex; align-items: center; gap: 8px; font-size: 12px;
             color: var(--ink-soft); }}
  .dot {{ width: 8px; height: 8px; border-radius: 99px; background: var(--dim); flex: none; }}
  .dot.live {{ background: var(--good); }}
  .dot.off {{ background: var(--warn); }}
  .ask-row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .ask-row input[type="text"] {{ flex: 1 1 320px; min-width: 0; padding: 11px 14px;
    border: 1px solid var(--line); border-radius: 8px; background: var(--ground);
    color: var(--ink); font: inherit; }}
  .ask-row select {{ padding: 11px 12px; border: 1px solid var(--line); border-radius: 8px;
    background: var(--ground); color: var(--ink); font: inherit; }}
  .ask-row button {{ padding: 11px 22px; border: none; border-radius: 8px;
    background: var(--accent); color: var(--surface); font: inherit; font-weight: 600;
    cursor: pointer; }}
  .ask-row button:disabled {{ opacity: .5; cursor: default; }}
  input:focus-visible, select:focus-visible, button:focus-visible, .sug:focus-visible {{
    outline: 2px solid var(--accent); outline-offset: 2px; }}
  .sugs {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .sug {{ font: inherit; font-size: 12px; padding: 5px 12px; border-radius: 99px;
    border: 1px solid var(--line); background: var(--ground); color: var(--ink-soft);
    cursor: pointer; text-align: left; }}
  .sug:hover {{ border-color: var(--accent); color: var(--accent); }}
  .answer {{ background: var(--accent-soft); border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0; padding: 14px 18px; }}
  .answer h4 {{ margin: 0 0 6px; font-size: 11px; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; color: var(--accent); }}
  .answer p {{ margin: 0; white-space: pre-wrap; }}
  .hits {{ display: flex; flex-direction: column; gap: 10px; margin-top: 14px; }}
  .hit {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }}
  .hit-top {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    margin-bottom: 6px; font-size: 11px; }}
  .rank {{ font-weight: 600; color: var(--dim);
    font-family: "JetBrains Mono", monospace; }}
  .hit p {{ margin: 0; font-size: 13px; color: var(--ink-soft); }}
  .warnbox {{ background: var(--warn-soft); border-left: 3px solid var(--warn);
    border-radius: 0 8px 8px 0; padding: 12px 16px; font-size: 13px;
    margin-bottom: 14px; }}
  .warnbox code {{ font-family: "JetBrains Mono", monospace; font-size: 12px; }}

  @media (max-width: 720px) {{
    .thesis, .ab {{ grid-template-columns: 1fr; }}
    table {{ min-width: 560px; }}
  }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
</style>

<div class="wrap">

  <header>
    <p class="eyebrow">Lab 07 · K4-L3B · nhóm sieunhandienquang</p>
    <h1>Truy xuất chính sách trả hàng Shopee</h1>
    <p class="sub">10 tài liệu công khai từ Trung tâm trợ giúp Shopee, 5 câu hỏi đánh giá,
      3 chiến lược chia nhỏ văn bản. Mọi con số dưới đây sinh trực tiếp từ
      <span class="mono">ket_qua_benchmark.txt</span>.</p>
  </header>

  <section>
    <h2><span class="n">01</span>Điều chi phối kết quả không phải cách chunk</h2>
    <p class="lede">Cùng corpus, cùng 5 câu hỏi, cùng
      <span class="mono">FixedSizeChunker(300, 50)</span> — khác nhau duy nhất ở mô hình nhúng.</p>
    <div class="thesis">
      <div class="big is-mock">
        <p class="cap">Mock&nbsp;Embedder</p>
        <p class="val">{mock['tong']}<span style="font-size:.4em;color:var(--ink-soft)"> / 10</span></p>
        <p class="engine">{e(mock['embedder'])} · {mock['chunks']} chunk</p>
        {bar(mock['tong'], 10, 'warn')}
      </div>
      <div class="big is-real">
        <p class="cap">Embedder thật</p>
        <p class="val">{real['tong']}<span style="font-size:.4em;color:var(--ink-soft)"> / 10</span></p>
        <p class="engine">{e(real['embedder'])} · {real['chunks']} chunk</p>
        {bar(real['tong'], 10, 'good')}
      </div>
    </div>
    <p class="callout">Chênh lệch <strong>{delta} điểm</strong> chỉ do chất lượng embedding.
      Trong khi đó ba chiến lược chunking khác nhau, đo trên cùng nền mock, chỉ chênh nhau
      <strong>1 điểm</strong>. Khi nền đo là nhiễu thì mọi so sánh chiến lược đều vô nghĩa.</p>
  </section>

  <section>
    <h2><span class="n">02</span>Ba chiến lược của nhóm</h2>
    <p class="lede">Cùng đo trên <span class="mono">MockEmbedder</span> để ba kết quả so sánh
      được với nhau. Số chunk chênh gần gấp đôi, điểm truy xuất gần như không đổi.</p>
    <div class="scroll">
      <table>
        <thead><tr>
          <th>Thành viên &amp; chiến lược</th><th class="num">Chunk</th>
          <th class="num">Dài TB</th><th class="num">Điểm</th><th>Mạnh / yếu</th>
        </tr></thead>
        <tbody>{''.join(hang_team)}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2><span class="n">03</span>Metadata filter làm được gì</h2>
    <p class="lede">Câu hỏi 5 chạy hai lần trên cùng một kho vector, chỉ khác tham số
      <span class="mono">metadata_filter</span>.</p>
    <div class="ab">{ab_html}</div>
    <p class="callout">Nhưng khi chạy lại bằng embedder thật, <strong>hai lần cho kết quả
      giống hệt nhau</strong> — embedding tốt đã tự tìm đúng tài liệu người bán vì câu hỏi
      chứa cụm “Kênh Quản Lý Shop” vốn chỉ có trong tài liệu đó. Theo tiêu chí của đề,
      câu hỏi này <strong>chưa thực sự “cần” filter</strong>; nó chỉ cần khi embedding yếu.</p>
  </section>

  <section>
    <h2><span class="n">04</span>Năm câu hỏi đánh giá</h2>
    <p class="lede">Chấm hai mức: tài liệu gold phải nằm trong top-3 <em>và</em> ngữ cảnh
      truy xuất được phải thật sự chứa chuỗi trả lời.</p>
    <div class="scroll">
      <table>
        <thead><tr>
          <th class="num">#</th><th>Câu hỏi &amp; đáp án chuẩn</th>
          <th class="num">Mock</th><th class="num">Gemini · top-1</th>
        </tr></thead>
        <tbody>{''.join(hang_query)}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2><span class="n">05</span>Vì sao phải cần metadata, không thể chỉ tin cosine</h2>
    <p class="lede">Năm cặp câu đo bằng <span class="mono">compute_similarity()</span> với
      <span class="mono">gemini-embedding-001</span>. Dự đoán ghi trước khi chạy.</p>
    <div class="scroll">
      <table>
        <thead><tr>
          <th class="num">#</th><th>Câu A</th><th>Câu B</th>
          <th class="num">Dự đoán</th><th class="num">Thực tế</th><th class="num">Đúng</th>
        </tr></thead>
        <tbody>{''.join(hang_cap)}</tbody>
      </table>
    </div>
    <p class="callout">Cặp 5 <strong>trái nghĩa nhau</strong> mà vẫn đạt
      <span class="mono">0.8379</span>; cặp 2 đổi chủ thể từ người mua sang người bán vẫn đạt
      <span class="mono">0.8600</span>. Cosine mã hoá chủ đề, không mã hoá phủ định hay chủ thể —
      những khác biệt đó buộc phải đưa vào metadata.</p>
  </section>


  <section>
    <h2><span class="n">06</span>Hỏi thử kho tri thức</h2>
    <p class="lede">Chạy trực tiếp <span class="mono">EmbeddingStore</span> và
      <span class="mono">KnowledgeBaseAgent</span> trong <span class="mono">src/</span>,
      chiến lược <span class="mono">FixedSizeChunker(300, 50)</span>.</p>

    <div class="ask">
      <p class="status"><span class="dot" id="dot"></span><span id="status">Đang kiểm tra server…</span></p>

      <form class="ask-row" id="form">
        <input type="text" id="cauhoi" autocomplete="off"
               placeholder="Ví dụ: Bao lâu thì được yêu cầu trả hàng hoàn tiền?">
        <select id="loc" aria-label="Lọc theo đối tượng">
          <option value="">Không lọc</option>
          <option value="buyer">audience = buyer</option>
          <option value="seller">audience = seller</option>
          <option value="both">audience = both</option>
        </select>
        <button type="submit" id="nut">Hỏi</button>
      </form>

      <div class="sugs" id="sugs"></div>
      <div id="ketqua"></div>
    </div>
  </section>

<script>
(function () {{
  var DUNG_SAN = {dung_san};
  var online = false;
  var dot = document.getElementById("dot");
  var status = document.getElementById("status");
  var form = document.getElementById("form");
  var oCauHoi = document.getElementById("cauhoi");
  var oLoc = document.getElementById("loc");
  var nut = document.getElementById("nut");
  var ketqua = document.getElementById("ketqua");

  function esc(t) {{
    var d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }}

  DUNG_SAN.forEach(function (m) {{
    var b = document.createElement("button");
    b.type = "button";
    b.className = "sug";
    b.textContent = m.cau_hoi.length > 66 ? m.cau_hoi.slice(0, 66) + "\u2026" : m.cau_hoi;
    b.title = m.cau_hoi;
    b.addEventListener("click", function () {{
      oCauHoi.value = m.cau_hoi;
      oLoc.value = m.loc ? "seller" : "";
      if (online) form.requestSubmit(); else ve(m, true);
    }});
    document.getElementById("sugs").appendChild(b);
  }});

  fetch("/api/health").then(function (r) {{
    return r.ok ? r.json() : Promise.reject(new Error("offline"));
  }}).then(function (d) {{
    online = true;
    dot.className = "dot live";
    status.textContent = "Server \u0111ang ch\u1ea1y \u00b7 " + d.chunks + " chunk \u00b7 " + d.chien_luoc;
  }}).catch(function () {{
    online = false;
    dot.className = "dot off";
    status.textContent = "Server ch\u01b0a ch\u1ea1y \u2014 b\u1ea5m c\u00e2u h\u1ecfi b\u00ean d\u01b0\u1edbi \u0111\u1ec3 xem k\u1ebft qu\u1ea3 \u0111\u00e3 l\u01b0u.";
    nut.disabled = true;
    oCauHoi.placeholder = "Ch\u1ea1y: python demo_server.py \u0111\u1ec3 h\u1ecfi c\u00e2u b\u1ea5t k\u1ef3";
  }});

  function ve(d, offline) {{
    var h = "";
    if (offline) {{
      h += '<div class="warnbox">K\u1ebft qu\u1ea3 \u0111\u00e3 l\u01b0u t\u1eeb <code>ket_qua_benchmark.txt</code>. '
         + 'Ch\u1ea1y <code>python demo_server.py</code> \u0111\u1ec3 h\u1ecfi c\u00e2u b\u1ea5t k\u1ef3.</div>';
    }}
    if (d.tra_loi) {{
      h += '<div class="answer"><h4>C\u00e2u tr\u1ea3 l\u1eddi c\u1ee7a agent</h4><p>'
         + esc(d.tra_loi) + "</p></div>";
    }}
    h += '<div class="hits">';
    (d.top || []).forEach(function (t, i) {{
      h += '<div class="hit"><div class="hit-top">'
        + '<span class="rank">#' + (i + 1) + "</span>"
        + (t.audience ? '<span class="aud aud-' + esc(t.audience) + '">' + esc(t.audience) + "</span>" : "")
        + '<span class="mono doc-id">' + esc(t.doc_id) + "</span>"
        + '<span class="mono" style="margin-left:auto;color:var(--ink-soft)">'
        + Number(t.score).toFixed(4) + "</span></div>"
        + "<p>" + esc(t.content) + "</p></div>";
    }});
    h += "</div>";
    ketqua.innerHTML = h;
  }}

  form.addEventListener("submit", function (ev) {{
    ev.preventDefault();
    var cauHoi = oCauHoi.value.trim();
    if (!cauHoi || !online) return;
    nut.disabled = true;
    nut.textContent = "\u0110ang h\u1ecfi\u2026";
    ketqua.innerHTML = '<p class="note">\u0110ang embed c\u00e2u h\u1ecfi v\u00e0 truy xu\u1ea5t\u2026</p>';
    fetch("/api/ask", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ cau_hoi: cauHoi, loc: oLoc.value || null }})
    }}).then(function (r) {{ return r.json(); }}).then(function (d) {{
      if (d.loi) ketqua.innerHTML = '<div class="warnbox">' + esc(d.loi) + "</div>";
      else ve(d, false);
    }}).catch(function (err) {{
      ketqua.innerHTML = '<div class="warnbox">Kh\u00f4ng g\u1ecdi \u0111\u01b0\u1ee3c server: '
        + esc(err) + "</div>";
    }}).finally(function () {{
      nut.disabled = false;
      nut.textContent = "H\u1ecfi";
    }});
  }});
}})();
</script>

  <footer>
    <p>Sinh bằng <span class="mono">python scripts/build_demo.py</span> từ
      <span class="mono">ket_qua_benchmark.txt</span> và
      <span class="mono">ket_qua_benchmark_mock.txt</span>.</p>
    <p>Nguyễn Hồng Thái · 2A202602894 · nhóm sieunhandienquang · lớp 3B</p>
  </footer>

</div>
"""


def _klass(diem: int, tren: int = 2) -> str:
    ty = diem / tren
    return "s-good" if ty >= 0.9 else "s-mid" if ty > 0 else "s-bad"


def main() -> int:
    real_path = ROOT / "ket_qua_benchmark.txt"
    mock_path = ROOT / "ket_qua_benchmark_mock.txt"
    for p in (real_path, mock_path):
        if not p.exists():
            print(f"Thieu {p.name} — chay bench.py truoc.")
            return 1

    out = ROOT / "demo.html"
    out.write_text(build(parse_run(real_path), parse_run(mock_path)), encoding="utf-8")
    print(f"Da sinh {out.name} ({out.stat().st_size:,} bytes) — mo bang trinh duyet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
