#!/usr/bin/env python3
"""Repair verified deployed URLs and preserve the editorial source of truth."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LINKS={
    "straddie-noticeboard-cloudflare": ("Straddie Noticeboard Network","https://straddie-noticeboard-cloudflare.auraofintelligence.workers.dev/"),
    "PLFC-members-club": ("Point Lookout Fishing Club Demo","https://plfc-clubhouse.auraofintelligence.workers.dev/"),
}
OLD="straddie-noticeboard-network"
def read(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))
def write(name,data):
    path=ROOT/name
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
    atlas=read("data/projects.json")
    manual=read("data/manual-projects.json")
    reviewed=read("data/reviewed-public-additions-2026-11-24.json")
    by_name={p["name"]:p for p in atlas["projects"]}
    manual_by_name={p["name"]:p for p in manual["projects"]}
    for name,(title,url) in LINKS.items():
        if name not in by_name or name not in manual_by_name:
            raise RuntimeError("Missing reviewed project "+name)
        for record in (by_name[name],manual_by_name[name]):
            record.update(title=title,publicPage=url)
        for record in reviewed["projects"]:
            if record["name"]==name:
                record.update(title=title,publicPage=url)
    old_title="Straddie Noticeboard Network (earlier prototype)"
    by_name[OLD]["title"]=old_title
    if OLD not in manual_by_name:
        manual_by_name[OLD]={"name":OLD,"title":old_title}
        manual["projects"].append(manual_by_name[OLD])
    else:
        manual_by_name[OLD]["title"]=old_title
    # Preserve the current and earlier build's direct lineage, evidenced in the
    # Cloudflare repository README, and its explicit cooperative relationships.
    pairs=[
        ("straddie-noticeboard-cloudflare",OLD,"Current Cloudflare build based on the earlier public prototype"),
        ("straddie-noticeboard-cloudflare","ready-set-co-op-trust-hub","Related cooperative planning; noticeboard proposed as its first project"),
        ("straddie-noticeboard-cloudflare","strange-but-true","Preparatory work and prototype held through Strange But True"),
    ]
    for a,b,reason in pairs:
        for src,dst in [(a,b),(b,a)]:
            p,q=by_name[src],by_name[dst]
            neighbours=p.setdefault("neighbours",[])
            if not any(x["name"]==dst for x in neighbours):
                neighbours.append({"name":dst,"title":q["title"],"repositoryUrl":q["repositoryUrl"],"publicPage":q.get("publicPage"),"labels":[reason],"directionalLabels":[],"confidence":"confirmed"})
            p["relationshipCount"]=len(neighbours)
    # Keep neighbour target metadata in sync with the canonical directory.
    for p in atlas["projects"]:
        for n in p.get("neighbours",[]):
            if n["name"] in (*LINKS,OLD):
                q=by_name[n["name"]]
                n["title"]=q["title"];n["publicPage"]=q.get("publicPage")
    # Maintain the edited link targets and connection overrides for future rebuilds.
    for name in set([x for a,b,_ in pairs for x in (a,b)]):
        if name not in manual_by_name:
            manual_by_name[name]={"name":name};manual["projects"].append(manual_by_name[name])
        manual_by_name[name]["neighbours"]=by_name[name]["neighbours"]
    for p in manual["projects"]:
        for n in p.get("neighbours",[]):
            if n["name"] in (*LINKS,OLD):
                q=by_name[n["name"]]
                n["title"]=q["title"];n["publicPage"]=q.get("publicPage")
    for name,data in [("data/projects.json",atlas),("data/manual-projects.json",manual),("data/reviewed-public-additions-2026-11-24.json",reviewed)]:
        write(name,data)
    for name,(title,url) in LINKS.items():
        print(name,url)
if __name__=="__main__":
    main()
