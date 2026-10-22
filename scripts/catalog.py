"""Crawl docs.informatica.com -> catalog.json (product, tier, latest version, DocSet zip, H2L articles)."""
import json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://docs.informatica.com"
UA = {"User-Agent": "Mozilla/5.0"}

# Priority tiers by URL prefix (estimated market share / usage). First match wins; default tier 4.
TIERS = [
    (1, ["integration-cloud/", "ipaas/", "cloud-common-services/", "release-information/",
         "data-integration/powercenter.", "data-integration/powerexchange", "data-integration/common-content"]),
    (2, ["data-governance-and-quality-cloud/", "data-quality-and-governance/", "data-catalog/",
         "data-engineering/", "claire/", "informatica-headless/"]),
    (3, ["master-data-management-cloud/", "master-data-management/"]),
]
LAB_RE = re.compile(r"lab|hands-on|tutorial|workshop|quick-?start|exercise", re.I)


def get(path):
    url = path if path.startswith("http") else BASE + path
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def follow(path):
    """Fetch page, following AEM meta-refresh redirects."""
    for _ in range(3):
        html = get(path)
        m = re.search(r'http-equiv="refresh" content="0;url=([^"]+)"', html)
        if not m:
            return path, html
        path = m.group(1).replace("/content/informaticadita-com/en_us", "")
    return path, html


def tier_of(path):
    return next((t for t, prefixes in TIERS if any(path.startswith(p) for p in prefixes)), 4)


def product(path):
    try:
        vpath, html = follow("/" + path)
    except Exception as e:
        return {"path": path, "error": str(e)}
    title = re.search(r"<title>([^<]+)", html)
    zips = sorted(set(re.findall(r'href="(/content/dam/source/doc-set-zips/[^"]+\.zip)"', html)))
    h2l = sorted(set(re.findall(r'href="(?:https://docs\.informatica\.com)?(/[^"]+/h2l/[^"]+\.html)"', html)))
    return {"path": path, "tier": tier_of(path), "title": title.group(1).strip() if title else path,
            "version_page": vpath, "zips": zips, "h2l": h2l}


def main(out):
    home = get("/")
    paths = sorted({m for m in re.findall(r'href="/([a-z0-9-]+/[^"/]+\.html)"', home)
                    if not m.startswith(("etc", "content"))})
    with ThreadPoolExecutor(8) as ex:
        cat = list(ex.map(product, paths))
    json.dump(sorted(cat, key=lambda p: (p.get("tier", 9), p["path"])), open(out, "w"), indent=1)
    print(f"products={len(cat)} errors={sum('error' in p for p in cat)} "
          f"zips={sum(len(p.get('zips', [])) for p in cat)} h2l={len({h for p in cat for h in p.get('h2l', [])})}")


if __name__ == "__main__":
    main(sys.argv[1])
