"""Download DocSet zips + H2L PDFs from catalog.json, in tier order, into <root>/docs/."""
import io, json, re, sys, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from catalog import BASE, UA, follow

TIER_NAMES = {1: "1_Integration", 2: "2_DataQuality_Governance_Catalog", 3: "3_MDM", 4: "4_Others"}


def fetch(path):
    with urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=300) as r:
        return r.read()


def product_dir(root, p):
    kind = "Cloud" if p["version_page"].endswith(("current-version.html", "preface.html")) else "OnPrem"
    version = p["version_page"].rsplit("/", 1)[-1].removesuffix(".html")
    slug = p["path"].replace("/", "__").removesuffix(".html")
    return root / "docs" / TIER_NAMES[p["tier"]] / f"{kind}__{slug}__{version}"


def get_zip(dest, z):
    out = dest / "guides"
    if out.exists() and any(out.iterdir()):
        return None
    zipfile.ZipFile(io.BytesIO(fetch(z))).extractall(out)  # extractall strips ../ and absolute paths
    return None


def get_h2l(dest, h):
    name = h.split("/h2l/", 1)[1].split("/")[0].removesuffix(".html")  # not last segment: many end in abstract.html
    target = dest / "h2l" / f"{name}.pdf"
    if target.exists():
        return None
    _, html = follow(h)
    m = re.search(r'href="(/content/dam/[^"]+\.pdf)"', html)
    if not m:
        return f"NO_PDF {h}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(fetch(m.group(1)))
    return None


def safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:
        return f"ERROR {a[-1]} {e}"


def main(root, max_tier):
    root = Path(root)
    cat = [p for p in json.load(open(root / "catalog.json")) if p["tier"] <= max_tier]
    jobs = [(get_zip, product_dir(root, p), z) for p in cat for z in p["zips"]]
    jobs += [(get_h2l, product_dir(root, p), h) for p in cat for h in p["h2l"]]
    with ThreadPoolExecutor(6) as ex:
        fails = [r for r in ex.map(lambda j: safe(*j), jobs) if r]
    (root / "failures.txt").write_text("\n".join(fails))
    print(f"jobs={len(jobs)} failures={len(fails)}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
