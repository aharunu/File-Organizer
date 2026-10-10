# CS50 File Organizer

A Python command-line tool for grouping files by extension, initial letter or
size. This CS50 learning project now previews moves and records them for undo.
Only regular files directly inside your selected folder are organized.
Subfolders, hidden files, symbolic links and Windows junctions are left alone.

## Requirements

Python 3.10 or newer. No third-party packages are required.

## Usage

```powershell
git clone https://github.com/aharunu/File-Organizer.git
cd File-Organizer

# Preview; nothing is moved.
python main.py "C:\Documents\example" --by extension

# Apply the displayed plan.
python main.py "C:\Documents\example" --by extension --apply

# Preview undo, then restore the recorded files.
python main.py "C:\Documents\example" --undo
python main.py "C:\Documents\example" --undo --apply
```

Use `--by name` or `--by size` for other grouping modes. Run `python main.py`
without a path to enter one interactively. Preview is always the default.

## Grouping rules

- **Extension:** `report.PDF` goes to `pdf/report.PDF`. Extensionless files
  and unusual extensions go to `No Extension`.
- **Name:** `report.pdf` goes to `R/report.pdf`. Non-alphanumeric initials
  go to `Other`.
- **Size:** sizes use exact bytes and binary KB/MB/GB boundaries:

| Size | Folder |
| --- | --- |
| 0 to less than 16 KB | Very Small (0-16 KB) |
| 16 KB to less than 1 MB | Small (16 KB - 1 MB) |
| 1 MB to less than 128 MB | Medium (1-128 MB) |
| 128 MB to less than 1 GB | Large (128 MB - 1 GB) |
| 1 GB or more | Very Large (1 GB+) |

Empty files belong to the first size bucket; folders are never classified as
zero-sized files.

## Undo and file preservation

Applying a plan creates `.file-organizer.json` before any moves. Keep that
record until you undo the operation. A second grouping operation is refused
while a record exists.

Undo restores only the recorded files. It never flattens unrelated folders.
Existing destination files cause an error rather than being overwritten.
Only empty folders created by this operation are removed after undo;
pre-existing folders and newly added contents are retained.

Moves use exclusive hard links followed by removal of the old filename. This
preserves file bytes and metadata and prevents destination replacement. The
folder must be on a filesystem supporting hard links (for example NTFS or
ext4). FAT/exFAT and some network shares are not supported. Do not modify the
folder concurrently while applying or undoing a plan.

If a move fails, the record remains so `--undo` can restore completed moves.
If interrupted between link creation and removal of the old filename, both
names may exist. Undo refuses that conflict and keeps both copies/names for
manual inspection. Do not edit the operation record or rename recorded files.

Old versions did not produce a record; their grouping cannot be automatically
undone by this version. Restore those files manually.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use disposable folders and verify grouping, exact size boundaries,
collisions, recorded undo, interrupted operations and path/link validation.
Windows and Linux test jobs are defined under `.github/workflows/`.

## Original project material

The [CS50P video demo](https://youtu.be/0MRLsabARyc) and `script.txt` describe
the original version. Their directory-moving and flattening behavior has been
replaced by the rules above. `recover/main.py` now forwards to the maintained
entry point instead of running a second unsafe implementation.

Licensed under the MIT License; see `LICENSE`.
