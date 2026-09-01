#!/usr/bin/env python3
"""Build the public-safe data file used by Project Atlas.

The source audit is intentionally richer than the published Atlas data. This
script keeps only the fields people need to navigate public work. It supports a
small manual curation file so projects completed after an audit can be added
without hand-editing the generated output.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


ACCOUNT = "auraofintelligence"
REPOSITORY_PREFIX = f"https://github.com/{ACCOUNT}/"
HTTP_URL = re.compile(r"^https://[^\s]+$", re.IGNORECASE)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def clean_url(value: Any, *, allow_blank: bool = True) -> str | None:
    url = clean_text(value)
    if not url and allow_blank:
        return None
    if not HTTP_URL.match(url):
        raise ValueError(f"Expected a public HTTPS URL, got {url!r}")
    return url


def clean_date(value: Any) -> str | None:
    date = clean_text(value)
    if not date:
        return None
    if not ISO_DATE.match(date):
        raise ValueError(f"Expected YYYY-MM-DD build date, got {date!r}")
    dt.date.fromisoformat(date)
    return date


def display_name(name: str) -> str:
    special_names = {
        "auraofintelligence.github.io": "Aura of Intelligence home",
    }
    if name in special_names:
        return special_names[name]
    if name.startswith("i-C-"):
        return "i-C " + display_name(name.removeprefix("i-C-"))
    acronyms = {
        "ai": "AI",
        "gajra": "GAJRA",
        "plfc": "PLFC",
        "p4a": "P4A",
        "sbt": "SBT",
        "ssb": "SSB",
        "un": "UN",
        "qld": "QLD",
    }
    small_words = {"a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "the", "to"}
    words = [word for word in re.split(r"[_-]+", name) if word]
    title_words: list[str] = []
    for index, word in enumerate(words):
        lowered = word.casefold()
        if word.isupper() and len(word) > 1:
            title_words.append(word)
        elif lowered in acronyms:
            title_words.append(acronyms[lowered])
        elif index and lowered in small_words:
            title_words.append(lowered)
        else:
            title_words.append(word[:1].upper() + word[1:])
    return " ".join(title_words)


def public_repository_url(value: Any) -> str:
    url = clean_url(value, allow_blank=False)
    if not url.startswith(REPOSITORY_PREFIX):
        raise ValueError(f"Repository is outside the public {ACCOUNT} account: {url!r}")
    return url


def clean_labels(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [clean_text(value) for value in values if clean_text(value)]


def clean_family(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    title = clean_text(value.get("title"))
    if not title:
        return {}
    return {
        "id": clean_text(value.get("id")),
        "title": title,
        "role": clean_text(value.get("role")) or "member",
    }


def canonical_name(value: Any, names_by_fold: dict[str, str]) -> str:
    name = clean_text(value)
    canonical = names_by_fold.get(name.casefold())
    if not canonical:
        raise ValueError(f"Project is outside the audit: {name!r}")
    return canonical


def clean_neighbour(value: Any, names_by_fold: dict[str, str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Relationship entry must be an object")
    name = canonical_name(value.get("name"), names_by_fold)
    return {
        "name": name,
        "title": display_name(name),
        "repositoryUrl": public_repository_url(value.get("repositoryUrl")),
        "publicPage": clean_url(value.get("publicPage")),
        "labels": clean_labels(value.get("labels")),
        "directionalLabels": clean_labels(value.get("directionalLabels")),
        "confidence": clean_text(value.get("confidence")) or "not stated",
    }


def public_project_from_row(row: dict[str, str], relation: dict[str, Any], names_by_fold: dict[str, str]) -> dict[str, Any]:
    name = clean_text(row.get("name"))
    if not name:
        raise ValueError("Audit contains a project without a name")
    description = clean_text(row.get("proposed_about_description")) or clean_text(row.get("about_description"))
    neighbours = [clean_neighbour(item, names_by_fold) for item in relation.get("neighbours", [])]
    return {
        "name": name,
        "title": display_name(name),
        "repositoryUrl": public_repository_url(row.get("repository_url")),
        "publicPage": clean_url(row.get("public_page_url")),
        "firstBuilt": clean_date(row.get("first_built_date")),
        "buildStatus": clean_text(row.get("build_status")) or "not evidenced",
        "buildConfidence": clean_text(row.get("build_confidence")) or "not stated",
        "buildEvidence": clean_text(row.get("build_evidence")),
        "description": description or "Public project description to be confirmed.",
        "priority": clean_text(row.get("priority")),
        "readmeBand": clean_text(row.get("live_readme_band")) or "not assessed",
        "families": [family for family in (clean_family(item) for item in relation.get("families", [])) if family],
        "neighbours": neighbours,
        "relationshipCount": len(neighbours),
        "freshlyCompleted": False,
        "meaningfulRebuild": None,
        "source": "audit",
    }


MANUAL_KEYS = {
    "title",
    "repositoryUrl",
    "publicPage",
    "firstBuilt",
    "buildStatus",
    "buildConfidence",
    "buildEvidence",
    "description",
    "priority",
    "readmeBand",
    "families",
    "neighbours",
    "freshlyCompleted",
    "meaningfulRebuild",
    "replaceNeighbourNames",
}


def clean_manual_project(raw: Any, names_by_fold: dict[str, str]) -> tuple[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ValueError("Manual project must be an object")
    name = clean_text(raw.get("name"))
    if not name:
        raise ValueError("Manual project needs a name")
    unknown = set(raw) - (MANUAL_KEYS | {"name"})
    if unknown:
        raise ValueError(f"Manual project {name!r} includes unsupported keys: {sorted(unknown)}")

    cleaned: dict[str, Any] = {}
    for key in MANUAL_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "repositoryUrl":
            cleaned[key] = public_repository_url(value)
        elif key == "publicPage":
            cleaned[key] = clean_url(value)
        elif key == "firstBuilt":
            cleaned[key] = clean_date(value)
        elif key == "families":
            if not isinstance(value, list):
                raise ValueError(f"Manual project {name!r} families must be a list")
            cleaned[key] = [family for family in (clean_family(item) for item in value) if family]
        elif key == "neighbours":
            if not isinstance(value, list):
                raise ValueError(f"Manual project {name!r} neighbours must be a list")
            cleaned[key] = [clean_neighbour(item, names_by_fold | {name.casefold(): name}) for item in value]
        elif key == "freshlyCompleted":
            cleaned[key] = bool(value)
        elif key == "meaningfulRebuild":
            cleaned[key] = clean_meaningful_rebuild(value)
        elif key == "replaceNeighbourNames":
            if not isinstance(value, list):
                raise ValueError(f"Manual project {name!r} replaceNeighbourNames must be a list")
            cleaned[key] = [canonical_name(item, names_by_fold) for item in value]
        else:
            cleaned[key] = clean_text(value)

    if name.casefold() not in names_by_fold and "repositoryUrl" not in cleaned:
        raise ValueError(f"New manual project {name!r} needs a public repositoryUrl")
    return name, cleaned


def clean_meaningful_rebuild(value: Any, default_published: str | None = None) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("meaningfulRebuild must be an object")
    started = clean_date(value.get("started") or value.get("rebuildStarted"))
    published = clean_date(value.get("published") or value.get("currentReleaseDate") or default_published)
    status = clean_text(value.get("status"))
    title = clean_text(value.get("title")) or "Meaningful rebuild"
    if not started and not published:
        raise ValueError("meaningfulRebuild needs a rebuild start or release date")
    return {"title": title, "started": started or "", "published": published or "", "status": status}


def make_delta_project(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("New public project in delta must be an object")
    name = clean_text(raw.get("name"))
    if not name:
        raise ValueError("New public project in delta has no name")
    title = clean_text(raw.get("title")) or display_name(name)
    first_built = clean_date(raw.get("firstBuilt"))
    if not first_built:
        raise ValueError(f"New public project {name!r} needs an original build date")
    date_note = clean_text(raw.get("dateNote"))
    return {
        "name": name,
        "title": title,
        "repositoryUrl": public_repository_url(raw.get("repositoryUrl")),
        "publicPage": clean_url(raw.get("publicPage")),
        "firstBuilt": first_built,
        "buildStatus": "evidenced",
        "buildConfidence": "confirmed in post-audit refresh",
        "buildEvidence": date_note or "Original build date confirmed in the post-audit public refresh.",
        "description": f"{title} is a newly completed public project added after the August audit snapshot. Open its public page for the current project description.",
        "priority": "freshly completed",
        "readmeBand": "published after audit snapshot",
        "families": [],
        "neighbours": [],
        "relationshipCount": 0,
        "freshlyCompleted": True,
        "meaningfulRebuild": None,
        "source": "post-audit refresh",
    }


def add_neighbour(project: dict[str, Any], target: dict[str, Any], label: str) -> None:
    existing_names = {item.get("name", "").casefold() for item in project.get("neighbours", [])}
    if target["name"].casefold() in existing_names:
        return
    project["neighbours"].append(
        {
            "name": target["name"],
            "title": target["title"],
            "repositoryUrl": target["repositoryUrl"],
            "publicPage": target.get("publicPage"),
            "labels": [label],
            "directionalLabels": [],
            "confidence": "confirmed",
        }
    )


def apply_delta(delta: Any, project_by_name: dict[str, dict[str, Any]]) -> dict[str, str]:
    if not isinstance(delta, dict):
        raise ValueError("Delta file must contain an object")
    refreshed_date = clean_date(delta.get("refreshedDate"))
    if not refreshed_date:
        raise ValueError("Delta file needs a refreshedDate")
    project_by_fold = {name.casefold(): name for name in project_by_name}
    new_projects = delta.get("newPublicProjects", [])
    if not isinstance(new_projects, list):
        raise ValueError("Delta newPublicProjects must be a list")

    new_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for raw in new_projects:
        record = make_delta_project(raw)
        if record["name"].casefold() in project_by_fold:
            raise ValueError(f"Delta project already exists in Atlas data: {record['name']!r}")
        project_by_name[record["name"]] = record
        project_by_fold[record["name"].casefold()] = record["name"]
        new_records.append((raw, record))

    for raw, record in new_records:
        neighbours = raw.get("neighbours", [])
        if not isinstance(neighbours, list):
            raise ValueError(f"Delta project {record['name']!r} neighbours must be a list")
        for raw_name in neighbours:
            target_name = project_by_fold.get(clean_text(raw_name).casefold())
            if not target_name:
                raise ValueError(f"Delta project {record['name']!r} refers to an unknown public neighbour {raw_name!r}")
            target = project_by_name[target_name]
            add_neighbour(record, target, f"direct public-project link in the {refreshed_date} refresh")
            add_neighbour(target, record, f"newly completed project linked in the {refreshed_date} refresh")

    for release in delta.get("meaningfulReleases", []):
        if not isinstance(release, dict):
            raise ValueError("Delta meaningful release must be an object")
        raw_name = clean_text(release.get("name"))
        canonical_name = project_by_fold.get(raw_name.casefold())
        if not canonical_name:
            raise ValueError(f"Meaningful release refers to an unknown project {raw_name!r}")
        project_by_name[canonical_name]["meaningfulRebuild"] = clean_meaningful_rebuild(
            {
                "title": release.get("title"),
                "rebuildStarted": release.get("rebuildStarted"),
                "currentReleaseDate": refreshed_date,
                "status": release.get("status"),
            },
            refreshed_date,
        )

    for project in project_by_name.values():
        project["relationshipCount"] = len(project.get("neighbours", []))
    return {"refreshedDate": refreshed_date, "publicRepositoryCount": str(delta.get("publicRepositoryCount") or "")}


def clean_lineages(
    raw_lineages: Any,
    names_by_fold: dict[str, str],
    project_dates: dict[str, str | None],
) -> list[dict[str, Any]]:
    if not isinstance(raw_lineages, list):
        return []
    lineages: list[dict[str, Any]] = []
    for lineage in raw_lineages:
        if not isinstance(lineage, dict):
            continue
        stages = []
        for stage in lineage.get("stages", []):
            if not isinstance(stage, dict):
                continue
            try:
                repository = canonical_name(stage.get("repository"), names_by_fold)
            except ValueError:
                continue
            stages.append(
                {
                    "repository": repository,
                    "title": display_name(repository),
                    "order": int(stage.get("order") or len(stages) + 1),
                    "role": clean_text(stage.get("role")),
                    # The audit CSV is the canonical date record. Some lineage
                    # notes use human text such as "inherited history" instead
                    # of a machine-readable date, so do not publish that as a
                    # date field.
                    "firstBuilt": project_dates.get(repository),
                }
            )
        if len(stages) > 1:
            lineages.append(
                {
                    "id": clean_text(lineage.get("id")),
                    "title": clean_text(lineage.get("title")) or "Project lineage",
                    "description": clean_text(lineage.get("description")),
                    "confidence": clean_text(lineage.get("confidence")) or "not stated",
                    "stages": sorted(stages, key=lambda item: item["order"]),
                }
            )
    return lineages


def main() -> int:
    parser = argparse.ArgumentParser(description="Build public-safe Project Atlas data")
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--relations", type=Path, required=True)
    parser.add_argument("--delta", type=Path, help="Optional public post-audit refresh file")
    parser.add_argument("--manual", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.audit_csv.open(encoding="utf-8-sig", newline="") as handle:
        audit_rows = list(csv.DictReader(handle))
    if not audit_rows:
        raise ValueError("Audit CSV has no project rows")
    known_names = {clean_text(row.get("name")) for row in audit_rows}
    if len(known_names) != len(audit_rows) or "" in known_names:
        raise ValueError("Audit project names must be present and unique")
    names_by_fold = {name.casefold(): name for name in known_names}
    if len(names_by_fold) != len(known_names):
        raise ValueError("Audit project names must be unique without regard to case")

    relationships = read_json(args.relations)
    relation_by_fold = {
        clean_text(item.get("name")).casefold(): item
        for item in relationships.get("repositories", [])
        if isinstance(item, dict) and clean_text(item.get("name"))
    }
    if set(relation_by_fold) != set(names_by_fold):
        missing = sorted(known_names - {names_by_fold[key] for key in relation_by_fold if key in names_by_fold})
        extra = sorted(key for key in relation_by_fold if key not in names_by_fold)
        raise ValueError(f"Relationship project names differ from audit. Missing={missing}; extra={extra}")
    relation_by_name = {name: relation_by_fold[name.casefold()] for name in known_names}

    projects = [public_project_from_row(row, relation_by_name[clean_text(row["name"])], names_by_fold) for row in audit_rows]
    project_by_name = {project["name"]: project for project in projects}

    delta_metadata: dict[str, str] = {}
    if args.delta:
        delta_metadata = apply_delta(read_json(args.delta), project_by_name)

    manual = read_json(args.manual)
    manual_projects = manual.get("projects", []) if isinstance(manual, dict) else []
    if not isinstance(manual_projects, list):
        raise ValueError("manual-projects.json must contain a projects list")
    for raw in manual_projects:
        names_after_delta = {project_name.casefold(): project_name for project_name in project_by_name}
        name, changes = clean_manual_project(raw, names_after_delta)
        canonical_name = names_after_delta.get(name.casefold())
        if canonical_name:
            replacement_neighbours = changes.pop("replaceNeighbourNames", None)
            project = project_by_name[canonical_name]
            project.update(changes)
            if replacement_neighbours is not None:
                project["neighbours"] = []
                for neighbour_name in replacement_neighbours:
                    target = project_by_name[neighbour_name]
                    add_neighbour(project, target, "current verified public-project link")
                    add_neighbour(target, project, "current verified public-project link")
                project["relationshipCount"] = len(project["neighbours"])
            project_by_name[canonical_name]["source"] = "audit-plus-curation"
        else:
            project = {
                "name": name,
                "title": display_name(name),
                "repositoryUrl": changes["repositoryUrl"],
                "publicPage": None,
                "firstBuilt": None,
                "buildStatus": "curated",
                "buildConfidence": "curated",
                "buildEvidence": "Curated public addition after the audit snapshot.",
                "description": "Public project description to be confirmed.",
                "priority": "",
                "readmeBand": "not assessed",
                "families": [],
                "neighbours": [],
                "relationshipCount": 0,
                "freshlyCompleted": False,
                "meaningfulRebuild": None,
                "source": "curation",
            }
            project.update(changes)
            project["relationshipCount"] = len(project["neighbours"])
            project_by_name[name] = project

    for project in project_by_name.values():
        project["relationshipCount"] = len(project.get("neighbours", []))
    projects = sorted(project_by_name.values(), key=lambda item: item["name"].lower())
    output = {
        "schemaVersion": 1,
        "account": ACCOUNT,
        "auditSnapshotDate": clean_text(relationships.get("snapshotDate")),
        "refreshSnapshotDate": delta_metadata.get("refreshedDate"),
        "publicRepositoryCount": int(delta_metadata["publicRepositoryCount"]) if delta_metadata.get("publicRepositoryCount", "").isdigit() else None,
        "auditedProjectCount": len(audit_rows),
        "includedProjectCount": len(projects),
        "generatedOn": dt.date.today().isoformat(),
        "dateMethod": "Original build date is the earliest audited substantive project evidence in Brisbane local date. It is not GitHub's latest update date. A meaningful rebuild is shown separately so it never replaces the original date.",
        "relationshipMethod": "Every listed public neighbour is evidence-backed in the organisation audit. No arbitrary maximum has been applied.",
        "projects": projects,
        "lineages": clean_lineages(
            relationships.get("lineages"),
            {project_name.casefold(): project_name for project_name in project_by_name},
            {project_name: project.get("firstBuilt") for project_name, project in project_by_name.items()},
        ),
    }
    write_json(args.output, output)
    print(f"Built {args.output} with {len(projects)} projects ({len(audit_rows)} from audit, {len(projects) - len(audit_rows)} curated additions).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
