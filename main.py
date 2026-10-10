"""Preview, organize and undo file moves in a selected directory."""

import argparse
import json
import os
from pathlib import Path
import stat
import sys

JOURNAL = ".file-organizer.json"
STRATEGIES = ("extension", "name", "size")
SIZE_BUCKETS = (
    (16 * 1024, "Very Small (0-16 KB)"),
    (1024 * 1024, "Small (16 KB - 1 MB)"),
    (128 * 1024 * 1024, "Medium (1-128 MB)"),
    (1024 * 1024 * 1024, "Large (128 MB - 1 GB)"),
)


def is_link(path: Path) -> bool:
    """Include Windows junctions/reparse points, not only symbolic links."""
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def directory(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Directory not found: {root}")
    return root


def bucket_for(path: Path, strategy: str) -> str:
    if strategy == "extension":
        suffix = path.suffix.lstrip(".").lower()
        return suffix if suffix.isalnum() else "No Extension"
    if strategy == "name":
        first = path.name[0].upper()
        return first if first.isalnum() else "Other"
    if strategy == "size":
        size = path.stat().st_size
        for limit, label in SIZE_BUCKETS:
            if size < limit:
                return label
        return "Very Large (1 GB+)"
    raise ValueError(f"Unknown strategy: {strategy}")


def validate_bucket(root: Path, bucket: str) -> Path:
    path = root / bucket
    if path.exists() or path.is_symlink():
        if is_link(path) or not path.is_dir():
            raise ValueError(f"Grouping folder is a file or link: {bucket}")
    return path


def plan_moves(root: Path, strategy: str) -> list[dict[str, str]]:
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")
    journal = root / JOURNAL
    if journal.exists() or journal.is_symlink():
        raise ValueError("An operation record already exists. Run undo before organizing again.")
    moves = []
    for source in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if source.name.startswith(".") or is_link(source) or not source.is_file():
            continue
        bucket = bucket_for(source, strategy)
        destination = validate_bucket(root, bucket) / source.name
        if destination.exists() or destination.is_symlink():
            raise ValueError(f"Destination already exists: {bucket}/{source.name}")
        moves.append({"source": source.name, "destination": f"{bucket}/{source.name}"})
    return moves


def move_exclusive(source: Path, destination: Path) -> None:
    """Move on the same filesystem without replacing an existing destination."""
    if is_link(source) or not source.is_file():
        raise ValueError(f"Source is not a regular file: {source}")
    # Creating a hard link is exclusive: an existing destination causes failure.
    # If interrupted before unlink, both names remain; no file bytes are lost.
    os.link(source, destination, follow_symlinks=False)
    source.unlink()


def organize(root: Path, strategy: str, apply: bool = False) -> list[dict[str, str]]:
    moves = plan_moves(root, strategy)
    if not apply or not moves:
        return moves
    buckets = sorted({move["destination"].split("/")[0] for move in moves})
    created_dirs = [bucket for bucket in buckets if not (root / bucket).exists()]
    record = {"version": 1, "root": str(root), "moves": moves, "created_dirs": created_dirs}
    # Persist the complete plan before moving anything, including partial failures.
    with (root / JOURNAL).open("x", encoding="utf-8") as output:
        json.dump(record, output, indent=2, ensure_ascii=False)
        output.flush()
        os.fsync(output.fileno())
    for bucket in created_dirs:
        (root / bucket).mkdir()
    for move in moves:
        validate_bucket(root, move["destination"].split("/")[0])
        move_exclusive(root / move["source"], root / move["destination"])
    return moves


def safe_parts(value: object, length: int) -> tuple[str, ...]:
    if not isinstance(value, str) or "\\" in value or ":" in value:
        raise ValueError("Invalid path in operation record.")
    parts = tuple(value.split("/"))
    if len(parts) != length or any(
        not part or part in (".", "..") or part.startswith(".") for part in parts
    ):
        raise ValueError("Invalid path in operation record.")
    return parts


def load_record(root: Path) -> dict:
    journal = root / JOURNAL
    if journal.is_symlink() or (journal.exists() and is_link(journal)):
        raise ValueError("The operation record must not be a link.")
    if not journal.is_file():
        raise ValueError("No operation record found; unrelated folders will not be flattened.")
    record = json.loads(journal.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("version") != 1 or record.get("root") != str(root):
        raise ValueError("Invalid operation record or directory mismatch.")
    if not isinstance(record.get("moves"), list) or not isinstance(record.get("created_dirs"), list):
        raise ValueError("Invalid operation record.")
    sources, destinations, buckets = set(), set(), set()
    for move in record["moves"]:
        if not isinstance(move, dict) or set(move) != {"source", "destination"}:
            raise ValueError("Invalid move in operation record.")
        (source,) = safe_parts(move["source"], 1)
        bucket, filename = safe_parts(move["destination"], 2)
        if filename != source or source in sources or move["destination"] in destinations:
            raise ValueError("Invalid or duplicate move in operation record.")
        validate_bucket(root, bucket)
        sources.add(source)
        destinations.add(move["destination"])
        buckets.add(bucket)
    created = set()
    for value in record["created_dirs"]:
        (bucket,) = safe_parts(value, 1)
        if bucket not in buckets or bucket in created:
            raise ValueError("Invalid created directory in operation record.")
        created.add(bucket)
    return record


def undo(root: Path, apply: bool = False) -> list[dict[str, str]]:
    record = load_record(root)
    pending = []
    # Validate every move before restoring any files.
    for move in record["moves"]:
        original, grouped = root / move["source"], root / move["destination"]
        for candidate in (original, grouped):
            if candidate.exists() or candidate.is_symlink():
                if is_link(candidate) or not candidate.is_file():
                    raise ValueError(f"Recorded file is a folder or link: {candidate}")
        if original.exists() and grouped.exists():
            raise ValueError(f"Undo conflict: both paths exist for {move['source']}. No files overwritten.")
        if not original.exists() and not grouped.exists():
            raise ValueError(f"Recorded file is missing: {move['source']}")
        if grouped.exists():
            pending.append({"source": move["destination"], "destination": move["source"]})
    if apply:
        for move in pending:
            validate_bucket(root, move["source"].split("/")[0])
            move_exclusive(root / move["source"], root / move["destination"])
        for bucket in record["created_dirs"]:
            path = validate_bucket(root, bucket)
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
        (root / JOURNAL).unlink()
    return pending


def show_moves(moves: list[dict[str, str]], applied: bool) -> None:
    for move in moves:
        print(f"{move['source']} -> {move['destination']}")
    if not moves:
        print("No files to move.")
    elif applied:
        print(f"Moved {len(moves)} file(s).")
    else:
        print(f"Preview: {len(moves)} file(s). Run again with --apply to move them.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, help="Folder to organize")
    parser.add_argument("--by", choices=STRATEGIES, default="extension")
    parser.add_argument("--undo", action="store_true", help="Restore only recorded moves")
    parser.add_argument("--apply", action="store_true", help="Apply moves; default is preview")
    args = parser.parse_args(argv)
    try:
        selected = args.directory
        if selected is None:
            entered = input("Folder to organize: ").strip()
            if not entered:
                raise ValueError("A directory path is required.")
            selected = Path(entered)
        root = directory(selected)
        moves = undo(root, args.apply) if args.undo else organize(root, args.by, args.apply)
        show_moves(moves, args.apply)
        return 0
    except (OSError, ValueError, EOFError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
