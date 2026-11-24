#!/usr/bin/env python3
"""Reconcile the public Atlas against GitHub without publishing unreviewed projects.

Audit is read-only; --apply imports only explicitly reviewed records. Run from the
Atlas checkout. Network requests use GitHub's public REST API; no private sources.
"""
from __future__ import annotations
import argparse, base64, datetime as dt, io, json, os, re, subprocess, sys
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "auraofintelligence"
API = "https://api.github.com"
REVIEW = ROOT / "data/reviewed-public-additions-2026-11-24.json"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
SENSITIVE = re.compile(r"command[-_ ]?cent(?:re|er)|(?:^|[-_])private(?:$|[-_])|(?:^|[-_])secret(?:$|[-_])", re.I)

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Project-Atlas-public-audit", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urlopen(Request(API + path, headers=headers), timeout=40) as response:
        return json.load(response)

def live_repos():
    result = {}
    for page in range(1, 101):
        batch = api(f"/users/{ACCOUNT}/repos?type=owner&sort=full_name&direction=asc&per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected public repository response")
        for row in batch:
            if row.get("owner", {}).get("login", "").casefold() != ACCOUNT or row.get("private") or row.get("visibility", "public") != "public":
                continue
            result[row["name"].casefold()] = row
        if len(batch) < 100:
            return result
    raise RuntimeError("Public repository pagination did not terminate")

def public_page(url):
    if not url:
        return None
    u = urlparse(url)
    if u.scheme != "https" or not (u.hostname == f"{ACCOUNT}.github.io" or (u.hostname or "").endswith(f".{ACCOUNT}.workers.dev")):
        return None
    try:
        with urlopen(Request(url, headers={"User-Agent":"Project-Atlas-public-audit"}), timeout=20) as res:
            final = urlparse(res.geturl())
            if res.status == 200 and final.hostname == u.hostname:
                return url
    except Exception:
        pass
    return None

def icon_for(row, stem):
    from PIL import Image
    asset = ROOT / "assets/project-icons" / (stem + ".webp")
    colour = "#3f625b"
    name = row["name"]
    prefix = f"/repos/{ACCOUNT}/{quote(name, safe='')}"
    try:
        tree = api(prefix + "/git/trees/" + quote(row["default_branch"], safe="") + "?recursive=1")
        files = [x for x in tree.get("tree", []) if x.get("type") == "blob" and x.get("size", 0) <= 2_000_000 and re.search(r"(?:^|/)(?:favicon(?:[-_.][^/]*)?|apple-touch-icon(?:[-_.][^/]*)?|logo(?:[-_.][^/]*)?)\.(?:png|svg|ico|webp|jpe?g)$", x["path"], re.I)]
        files.sort(key=lambda x: ("favicon" not in x["path"].lower(), x["path"].count("/"), len(x["path"]), x["path"]))
        for item in files[:8]:
            try:
                blob = api(prefix + "/git/blobs/" + item["sha"])
                raw = base64.b64decode(blob["content"])
                if item["path"].lower().endswith(".svg"):
                    import cairosvg
                    raw = cairosvg.svg2png(bytestring=raw, output_width=128, output_height=128, unsafe=False)
                with Image.open(io.BytesIO(raw)) as im:
                    im = im.convert("RGBA")
                    im.thumbnail((128,128), Image.Resampling.LANCZOS)
                    canvas = Image.new("RGBA",(128,128),(255,255,255,0))
                    canvas.alpha_composite(im, ((128-im.width)//2,(128-im.height)//2))
                    canvas.save(asset, "WEBP", lossless=True)
                return {"asset":str(asset.relative_to(ROOT)).replace("\\","/"),"kind":"local-source","fallbackColour":colour,"source":name+"/"+item["path"]}
            except Exception:
                continue
    except Exception:
        pass
    Image.new("RGB",(128,128),colour).save(asset,"WEBP",lossless=True)
    return {"asset":str(asset.relative_to(ROOT)).replace("\\","/"),"kind":"colour-tile","fallbackColour":colour,"source":None}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    today=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=10)).date().isoformat()
    atlas_path=ROOT/"data/projects.json"
    dates_path=ROOT/"data/repository-creation-dates.json"
    manual_path=ROOT/"data/manual-projects.json"
    icons_path=ROOT/"data/project-icons.json"
    atlas,dates,manual,icons=map(load,(atlas_path,dates_path,manual_path,icons_path))
    approved=load(REVIEW)["projects"]
    approved_names={p["name"].casefold() for p in approved}
    current={p["name"].casefold():p for p in atlas["projects"]}
    excluded={name.casefold() for name in manual.get("excludedProjectNames",[])}
    repos=live_repos()
    active={k:v for k,v in repos.items() if not v.get("archived") and not v.get("disabled")}
    stale=[p["name"] for k,p in current.items() if k not in active or k in excluded or SENSITIVE.search(k)]
    eligible={k:v for k,v in active.items() if k not in excluded and not SENSITIVE.search(k)}
    missing=sorted(set(eligible)-set(current))
    pending=[p for p in approved if p["name"].casefold() in missing]
    report={"public_repositories":len(repos),"active_public_repositories":len(active),"atlas_projects":len(current),"reviewed_additions_pending":[p["name"] for p in pending],"other_public_candidates":[eligible[k]["name"] for k in missing if k not in approved_names],"withheld_count":len(set(active)-set(eligible)),"published_records_requiring_review":len(stale)}
    print(json.dumps(report,indent=2))
    if not args.apply:
        return
    if stale:
        raise RuntimeError("Published records require visibility/archive review; refusing to write a partial refresh.")
    if not pending:
        print("No approved public additions to apply.")
        return
    manual_by_name={p["name"].casefold():p for p in manual["projects"]}
    fallback=set(icons.get("approvedAdditionalFallbacks",[]))
    for p in pending:
        name=p["name"]; key=name.casefold(); row=eligible[key]
        if row["name"] != name or row.get("fork"):
            raise RuntimeError("Reviewed repository changed identity or is a fork: "+name)
        created=row.get("created_at")
        if not created:
            raise RuntimeError("Missing verified GitHub creation timestamp: "+name)
        dt.datetime.fromisoformat(created.replace("Z","+00:00"))
        url=f"https://github.com/{ACCOUNT}/{name}"
        if row.get("html_url") != url:
            raise RuntimeError("Repository URL mismatch: "+name)
        built=p.get("firstBuilt")
        if built:
            dt.date.fromisoformat(built)
        evidence=("Explicit public README build date: " if built else "Original substantive build date not yet verified; repository creation date is recorded separately. Public README: ")+p["source"]
        record={"name":name,"title":p["title"],"repositoryUrl":url,"publicPage":public_page(p.get("publicPage")),"firstBuilt":built,"buildStatus":"evidenced" if built else "date review pending","buildConfidence":"public README" if built else "not established","buildEvidence":evidence,"description":p["description"],"priority":"reviewed public addition","readmeBand":"public README reviewed","families":[],"neighbours":[],"freshlyCompleted":bool(built),"meaningfulRebuild":None}
        existing=manual_by_name.get(key)
        if existing is None:
            manual["projects"].append(record.copy())
        else:
            existing.update(record)
        atlas["projects"].append(dict(record,relationshipCount=0,source="curation",repositoryCreatedAt=created))
        dates["repositories"][name]=created
        stem=re.sub(r"[^a-z0-9_-]+","-",key).strip("-")
        if not stem or any(x.get("asset")==f"assets/project-icons/{stem}.webp" for x in icons["icons"].values()):
            raise RuntimeError("Icon filename collision: "+name)
        entry=icon_for(row,stem)
        icons["icons"][name]=entry
        if entry["kind"]=="colour-tile":
            fallback.add(name)
    atlas["projects"].sort(key=lambda x:x["name"].casefold())
    atlas["includedProjectCount"]=atlas["auditedProjectCount"]=len(atlas["projects"])
    atlas["publicRepositoryCount"]=len(repos)
    atlas["refreshSnapshotDate"]=atlas["generatedOn"]=today
    dates["verifiedOn"]=today
    icons["generatedOn"]=today
    icons["approvedAdditionalFallbacks"]=sorted(fallback)
    for path,data in ((atlas_path,atlas),(dates_path,dates),(manual_path,manual),(icons_path,icons)):
        save(path,data)
    subprocess.run(["npm","run","build:qr"],cwd=ROOT,check=True)
    subprocess.run([sys.executable,"scripts/validate_atlas.py"],cwd=ROOT,check=True)
    print(f"Validated {len(atlas['projects'])} Atlas records. No publication performed by this script.")

if __name__=="__main__":
    main()
