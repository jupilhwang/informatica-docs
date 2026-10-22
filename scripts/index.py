"""Build README.md index + 00_Lab_Guides/ (copies of tutorial/getting-started/quick-start PDFs)."""
import json, re, shutil, sys
from pathlib import Path
from download import TIER_NAMES, product_dir

LAB_RE = re.compile(r"(^|[^a-z])lab([^a-z]|$)|tutorial|hands.?on|exercise|workshop|getting.?started|quick.?start", re.I)
TIER_DESC = {1: "Integration (CDI, CDI-PC, CMI/DIR, CAI, PowerCenter, PowerExchange) — 최우선",
             2: "Data Quality / Governance / Catalog / Data Engineering / CLAIRE",
             3: "MDM (SaaS + On-Prem)", 4: "기타 (Data Security, DaaS, B2B, Replication, Ultra Messaging 등)"}


def main(root):
    root = Path(root)
    docs, labs = root / "docs", root / "docs" / "00_Lab_Guides"
    lab_rows = []
    for pdf in sorted(docs.glob("[1-4]_*/*/*/*.pdf")):
        if LAB_RE.search(pdf.stem):
            dest = labs / pdf.parts[-4] / f"{pdf.parts[-3]}__{pdf.name}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf, dest)
            lab_rows.append(f"| {pdf.parts[-4]} | {pdf.parts[-3]} | [{pdf.name}]({dest.relative_to(root).as_posix()}) |")
    out = ["# Informatica 문서 아카이브", "", "출처: https://docs.informatica.com (제품별 최신 버전 DocSet ZIP + How-To Library PDF)", "",
           "**브라우저로 보기: [index.html](index.html)** — 커리큘럼(P0~P11)·랩 가이드·전체 라이브러리·검색·PDF 뷰어 (`python3 scripts/spa.py .` 로 재생성)", "",
           "**Phase별 한 페이지 요약: [summaries/](summaries)** (P0~P11, SPA 각 Phase 카드에도 포함)", "",
           f"## 00. Lab / Tutorial / Getting Started ({len(lab_rows)}건)", "",
           "| Tier | 제품 | 문서 |", "|---|---|---|", *lab_rows, ""]
    for t, name in TIER_NAMES.items():
        out += [f"## {name} — {TIER_DESC[t]}", "", "| 제품 | 배포 | 버전 | 가이드 PDF | H2L PDF | 폴더 |", "|---|---|---|---|---|---|"]
        for p in json.load(open(root / "catalog.json")):
            if p["tier"] != t:
                continue
            d = product_dir(root, p)
            kind, ver = d.name.split("__")[0], d.name.rsplit("__", 1)[-1]
            g, h = (len(list((d / s).glob("**/*.pdf"))) if (d / s).exists() else 0 for s in ("guides", "h2l"))
            link = f"[열기]({d.relative_to(root).as_posix()})" if d.exists() else f"[웹 전용]({'https://docs.informatica.com/' + p['path']})"
            title = p["title"].split(" | ")[0].replace("&#39;", "'")
            if title in ("Preface", "POST data", "Current Version"):  # generic AEM titles on web-only pages
                title = p["path"].rsplit("/", 1)[-1].removesuffix(".html").replace("-", " ").title()
            out.append(f"| {title} | {kind} | {ver} | {g} | {h} | {link} |")
        out.append("")
    (root / "README.md").write_text("\n".join(out))
    print(f"labs={len(lab_rows)}")


if __name__ == "__main__":
    main(sys.argv[1])
