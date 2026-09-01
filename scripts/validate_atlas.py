#!/usr/bin/env python3
"""Lightweight checks for the static Project Atlas site and public data."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ACCOUNT = "auraofintelligence"
REPOSITORY_PREFIX = f"https://github.com/{ACCOUNT}/"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def valid_date(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def valid_https_url(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def qr_stem(value: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", value.lower()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate static Project Atlas files")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expected-audited", type=int, default=140)
    args = parser.parse_args()

    root = args.root.resolve()
    errors: list[str] = []
    for relative in (
        "index.html", "styles.css", "app.js", "package.json", "data/projects.json", "data/manual-projects.json",
        "scripts/build_atlas_data.py", "scripts/build_qr_codes.mjs",
    ):
        if not (root / relative).is_file():
            fail(errors, f"Missing required file: {relative}")

    if errors:
        print("Project Atlas validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    data = json.loads((root / "data/projects.json").read_text(encoding="utf-8"))
    manual = json.loads((root / "data/manual-projects.json").read_text(encoding="utf-8"))
    raw_excluded_names = manual.get("excludedProjectNames", []) if isinstance(manual, dict) else []
    if not isinstance(raw_excluded_names, list) or any(not isinstance(name, str) or not name for name in raw_excluded_names):
        fail(errors, "manual-projects.json excludedProjectNames must be a list of names")
        raw_excluded_names = []
    excluded_names = {name.casefold() for name in raw_excluded_names}
    projects = data.get("projects")
    if not isinstance(projects, list):
        fail(errors, "data/projects.json needs a projects list")
        projects = []

    if data.get("auditedProjectCount") != args.expected_audited:
        fail(errors, f"Expected {args.expected_audited} audited projects, found {data.get('auditedProjectCount')!r}")
    if data.get("includedProjectCount") != len(projects):
        fail(errors, "includedProjectCount does not match the projects list")
    if len(projects) < args.expected_audited:
        fail(errors, f"The public data has only {len(projects)} projects, expected at least {args.expected_audited}")
    if "not GitHub's latest update date" not in str(data.get("dateMethod")):
        fail(errors, "The date method must explicitly distinguish original build dates from GitHub update dates")

    names: set[str] = set()
    public_pages = 0
    relationship_total = 0
    qr_dir = root / "assets" / "qr"
    allowed_keys = {
        "name", "title", "repositoryUrl", "publicPage", "firstBuilt", "buildStatus", "buildConfidence", "buildEvidence",
        "description", "priority", "readmeBand", "families", "neighbours", "relationshipCount", "freshlyCompleted", "meaningfulRebuild", "source",
    }
    for project in projects:
        if not isinstance(project, dict):
            fail(errors, "Each project must be an object")
            continue
        extra_keys = set(project) - allowed_keys
        if extra_keys:
            fail(errors, f"Project {project.get('name')!r} includes non-public or unsupported fields: {sorted(extra_keys)}")
        name = project.get("name")
        if not isinstance(name, str) or not name:
            fail(errors, "A project has no name")
            continue
        if name.casefold() in names:
            fail(errors, f"Duplicate project name: {name}")
        names.add(name.casefold())
        if name.casefold() in excluded_names:
            fail(errors, f"Excluded project is still included in public data: {name}")
        if not isinstance(project.get("title"), str) or not project["title"]:
            fail(errors, f"Project {name} has no display title")
        repo_url = project.get("repositoryUrl")
        if not isinstance(repo_url, str) or not repo_url.startswith(REPOSITORY_PREFIX):
            fail(errors, f"Project {name} does not point to a public {ACCOUNT} repository")
        if not valid_https_url(project.get("publicPage")):
            fail(errors, f"Project {name} has an invalid public page URL")
        if project.get("publicPage"):
            public_pages += 1
        if not valid_date(project.get("firstBuilt")):
            fail(errors, f"Project {name} has an invalid original build date: {project.get('firstBuilt')!r}")
        rebuild = project.get("meaningfulRebuild")
        if rebuild is not None:
            if not isinstance(rebuild, dict):
                fail(errors, f"Project {name} has a malformed meaningful rebuild record")
            else:
                if not valid_date(rebuild.get("started") or None):
                    fail(errors, f"Project {name} has an invalid meaningful rebuild start date")
                if not valid_date(rebuild.get("published") or None):
                    fail(errors, f"Project {name} has an invalid meaningful release date")
        if not isinstance(project.get("description"), str) or not project["description"]:
            fail(errors, f"Project {name} has no public description")
        target = project.get("publicPage") or project.get("repositoryUrl")
        qr_path = qr_dir / f"{qr_stem(name)}.svg"
        if not qr_path.is_file():
            fail(errors, f"Project {name} has no generated QR SVG")
        else:
            qr_svg = qr_path.read_text(encoding="utf-8")
            if "<svg" not in qr_svg or "</svg>" not in qr_svg:
                fail(errors, f"Project {name} QR file is not an SVG")
            if f'data-project-atlas-target="{target}"' not in qr_svg:
                fail(errors, f"Project {name} QR file does not record its intended public target")
        neighbours = project.get("neighbours")
        if not isinstance(neighbours, list):
            fail(errors, f"Project {name} neighbours must be a list")
            neighbours = []
        if project.get("relationshipCount") != len(neighbours):
            fail(errors, f"Project {name} relationshipCount does not match its neighbours")
        relationship_total += len(neighbours)
        for neighbour in neighbours:
            if not isinstance(neighbour, dict):
                fail(errors, f"Project {name} has a malformed neighbour")
                continue
            neighbour_name = neighbour.get("name")
            if isinstance(neighbour_name, str) and neighbour_name.casefold() in excluded_names:
                fail(errors, f"Project {name} still links to excluded project {neighbour_name!r}")
            if not isinstance(neighbour_name, str) or neighbour_name.casefold() not in names and neighbour_name.casefold() not in {item.get('name', '').casefold() for item in projects if isinstance(item, dict)}:
                fail(errors, f"Project {name} links to a project outside this public data: {neighbour_name!r}")
            if not isinstance(neighbour.get("repositoryUrl"), str) or not neighbour["repositoryUrl"].startswith(REPOSITORY_PREFIX):
                fail(errors, f"Neighbour {neighbour_name!r} from {name} is not a public repository link")
            if not valid_https_url(neighbour.get("publicPage")):
                fail(errors, f"Neighbour {neighbour_name!r} from {name} has an invalid public page URL")

    if relationship_total < 1:
        fail(errors, "No evidence-backed relationships were generated")

    for lineage in data.get("lineages", []):
        for stage in lineage.get("stages", []):
            repository = stage.get("repository")
            if isinstance(repository, str) and repository.casefold() in excluded_names:
                fail(errors, f"Lineage {lineage.get('title')!r} still refers to excluded project {repository!r}")
            if not isinstance(repository, str) or repository.casefold() not in names:
                fail(errors, f"Lineage {lineage.get('title')!r} refers to a missing project {repository!r}")
            if not valid_date(stage.get("firstBuilt")):
                fail(errors, f"Lineage stage {repository!r} has an invalid original build date")

    expected_qr_files = {
        f"{qr_stem(project['name'])}.svg"
        for project in projects
        if isinstance(project, dict) and isinstance(project.get("name"), str)
    }
    actual_qr_files = {path.name for path in qr_dir.glob("*.svg")}
    stale_qr_files = sorted(actual_qr_files - expected_qr_files)
    if stale_qr_files:
        fail(errors, f"Generated QR directory has stale files: {stale_qr_files}")

    index = (root / "index.html").read_text(encoding="utf-8")
    css = (root / "styles.css").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    for marker in ("id=\"project-search\"", "id=\"fresh-grid\"", "id=\"print-directory-list\"", "id=\"lineage-grid\"", "data-print"):
        if marker not in index:
            fail(errors, f"index.html is missing required Atlas interface marker {marker}")
    for marker in ("@media print", ".qr-slot", ".qr-slot img", ".project-grid"):
        if marker not in css:
            fail(errors, f"styles.css is missing required style marker {marker}")
    for marker in ("data/projects.json", "relationshipDetails", "data-qr-url", "qrFilename", "freshlyCompleted"):
        if marker not in app:
            fail(errors, f"app.js is missing required behaviour marker {marker}")

    if errors:
        print("Project Atlas validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print(
        "Project Atlas validation passed: "
        f"{len(projects)} public projects, {public_pages} public pages, "
        f"{relationship_total} directed public relationships, {len(data.get('lineages', []))} lineages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
