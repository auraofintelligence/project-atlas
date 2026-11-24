#!/usr/bin/env python3
"""Check or repair em dashes in tracked UTF-8 project files and generated text."""
import argparse
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".html", ".htm", ".md", ".txt", ".json", ".jsonl", ".js", ".mjs", ".cjs", ".ts", ".css", ".py", ".yaml", ".yml", ".xml", ".svg", ".csv", ".tsv", ".toml"}
TOKEN = re.compile(chr(8212) + r"|&m" + r"dash;|&#0*8212;|&#x0*2014;|\\u" + "2014", re.I)

def normalise(text):
    return TOKEN.sub("-", text)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fix", action="store_true", help="Replace unwanted punctuation in place")
    parser.add_argument("paths", nargs="*", help="Optional explicit files; default is tracked project text")
    args = parser.parse_args()
    if args.paths:
        paths = [pathlib.Path(p).resolve() for p in args.paths]
    else:
        names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
        paths = [ROOT / name for name in names if name and pathlib.Path(name).suffix.lower() in TEXT_SUFFIXES and not set(pathlib.Path(name).parts).intersection({"node_modules", "vendor", ".venv"})]
    occurrences = 0
    for path in paths:
        if not path.is_file() or path.is_symlink():
            continue
        try:
            original = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            continue
        count = len(TOKEN.findall(original))
        if count:
            occurrences += count
            print(f"{path}: {count} forbidden punctuation occurrence(s)")
            if args.fix:
                path.write_bytes(normalise(original).encode("utf-8"))
    if occurrences and not args.fix:
        raise SystemExit(f"Punctuation check failed: {occurrences} occurrence(s)")
    print(f"Punctuation {'repair' if args.fix else 'check'}: {occurrences} occurrence(s) {'removed' if args.fix else 'found'}.")

if __name__ == "__main__":
    main()
