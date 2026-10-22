"""Build index.html (single-file SPA): curriculum phases + full library + lab guides."""
import json, re, subprocess, sys
from pathlib import Path
from download import TIER_NAMES, product_dir
from index import LAB_RE

HERE = Path(__file__).parent
# Undo camel-case splits that break product names.
FIXUPS = {"What S New": "What's New", "Saa S": "SaaS", "API S": "APIs", "Power Center": "PowerCenter",
          "Power Exchange": "PowerExchange", "Big Query": "BigQuery", "Net Weaver": "NetWeaver", "z OS": "z/OS",
          "Customer360": "Customer 360", "Product360": "Product 360",
          "Supplier360": "Supplier 360", "Reference360": "Reference 360"}
TIER_LABEL = {1: "Integration", 2: "Data Quality · Governance · Catalog", 3: "MDM", 4: "기타"}


def pretty(stem, h2l):
    """CDI_October2026_(REST-API)Reference_en -> 'REST API Reference'; 1297-secure-agent-x -> 'Secure Agent X'."""
    lang = " (DE)" if stem.endswith("_de") else ""
    stem = re.sub(r"_(en|de)$", "", stem)
    if h2l:
        t = re.sub(r"^_?\d+[-_]|[-_]H2L$", "", stem).replace("-", " ").replace("_", " ")
    else:
        t = stem.rsplit("_", 1)[-1] if "_" in stem and len(stem.rsplit("_", 1)[-1]) > 2 else stem
    t = re.sub(r"\(([^)]+)\)", lambda m: " " + m.group(1).replace("-", " ") + " ", t)
    t = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for a, b in FIXUPS.items():
        t = t.replace(a, b)
    return t[:1].upper() + t[1:] + lang


def build(root):
    root = Path(root)
    products, docs = [], []
    for p in json.load(open(root / "catalog.json")):
        d = product_dir(root, p)
        title = p["title"].split(" | ")[0].replace("&#39;", "'")
        if title in ("Preface", "POST data", "Current Version"):
            title = p["path"].rsplit("/", 1)[-1].removesuffix(".html").replace("-", " ").title()
        pi = len(products)
        products.append({"n": title, "t": p["tier"], "k": d.name.split("__")[0], "v": d.name.rsplit("__", 1)[-1],
                         "dir": d.name, "web": "https://docs.informatica.com/" + p["path"]})
        for pdf in sorted(d.glob("*/*.pdf")):
            h = pdf.parent.name == "h2l"
            docs.append({"p": pdf.relative_to(root).as_posix(), "t": pretty(pdf.stem, h), "f": pdf.stem,
                         "h": int(h), "l": int(bool(LAB_RE.search(pdf.stem))), "i": pi})
    phases, missing = json.load(open(HERE / "curriculum.json")), []
    for ph in phases:
        for s in ph["steps"]:
            rx = re.compile(s["f"], re.I)
            hit = next((n for n, x in enumerate(docs) if s["d"] in products[x["i"]]["dir"] and rx.search(re.sub(r"_(en|de)$", "", x["f"]))), None)
            s["doc"] = hit
            if hit is None:
                missing.append(f'{ph["id"]}: {s["d"]} / {s["f"]}')
    for ph in phases:  # one-page summaries; raw HTML disabled since text derives from untrusted PDFs
        md = root / "summaries" / f'{ph["id"]}.md'
        ph["summary"] = subprocess.run(["pandoc", "-f", "gfm-raw_html", "-t", "html"], input=md.read_text(),
                                       capture_output=True, text=True, check=True).stdout if md.exists() else ""
    data = {"products": products, "docs": docs, "phases": phases, "tiers": TIER_LABEL}
    html = (HERE / "spa_template.html").read_text().replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    (root / "index.html").write_text(html)
    print(f"products={len(products)} docs={len(docs)} labs={sum(d['l'] for d in docs)} "
          f"steps={sum(len(p['steps']) for p in phases)} missing={len(missing)} "
          f"summaries={sum(bool(p['summary']) for p in phases)}/{len(phases)}")
    print("\n".join(missing))
    return missing


if __name__ == "__main__":
    build(sys.argv[1])
