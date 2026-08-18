"""ChatGPT Image & Metadata Inspector CLI Utility."""

import argparse
import json
import sys
from pathlib import Path


def parse_metadata_file(path: Path) -> dict:
    """Parse and return metadata dictionary from a JSON file."""
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as err:
        print(f"[error] Failed to read {path}: {err}", file=sys.stderr)
        return {}


def scan_metadata_files(directory: Path) -> list[tuple[Path, dict]]:
    """Scan directory for *_metadata.json files and parse them."""
    if not directory.is_dir():
        return []
    results = []
    for json_file in sorted(directory.glob("*_metadata.json")):
        data = parse_metadata_file(json_file)
        if data:
            results.append((json_file, data))
    return results


def format_metadata_summary(path: Path, data: dict) -> str:
    """Format single metadata entry as human-readable summary string."""
    src = data.get("source", "unknown")
    ts = data.get("timestamp", "N/A")
    title = data.get("pageTitle", "N/A")
    dalle = data.get("dalle", {})
    prompt = dalle.get("prompt") or dalle.get("revised_prompt") or data.get("alt") or "N/A"
    return f"[{ts}] {path.name}\n  Title: {title}\n  Source: {src}\n  Prompt: {prompt[:80]}"


def main():
    """Main CLI entrypoint for inspecting image metadata."""
    parser = argparse.ArgumentParser(description="ChatGPT Image & Metadata Inspector")
    parser.add_argument("path", nargs="?", default=".", help="Directory or JSON file to inspect")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    if target.is_file() and target.suffix == ".json":
        data = parse_metadata_file(target)
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(format_metadata_summary(target, data))
            print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    dir_to_scan = target if target.is_dir() else target.parent
    entries = scan_metadata_files(dir_to_scan)
    if not entries:
        print(f"[info] No *_metadata.json files found in {dir_to_scan}")
        return

    print(f"[info] Found {len(entries)} metadata file(s) in {dir_to_scan}:\n")
    for p, d in entries:
        print(format_metadata_summary(p, d))
        print("-" * 60)


if __name__ == "__main__":
    main()
