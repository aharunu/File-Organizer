import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import main as organizer


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def file(self, name, data=b"example"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = organizer.main([str(argument) for argument in arguments])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_preview_has_no_side_effects(self):
        self.file("report.TXT")
        before = sorted(path.name for path in self.root.iterdir())
        plan = organizer.organize(self.root, "extension")
        self.assertEqual(plan, [{"source": "report.TXT", "destination": "txt/report.TXT"}])
        self.assertEqual(sorted(path.name for path in self.root.iterdir()), before)

    def test_group_and_undo_preserve_bytes(self):
        originals = {"report.TXT": b"hello\x00world", "photo.jpg": b"image", "README": b"read me"}
        for name, data in originals.items():
            self.file(name, data)
        organizer.organize(self.root, "extension", apply=True)
        self.assertEqual((self.root / "txt/report.TXT").read_bytes(), originals["report.TXT"])
        self.assertEqual((self.root / "No Extension/README").read_bytes(), originals["README"])
        self.assertTrue((self.root / organizer.JOURNAL).is_file())
        organizer.undo(self.root, apply=True)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, originals)

    def test_subdirectories_and_hidden_files_are_untouched(self):
        nested = self.file("unrelated/nested.txt", b"nested")
        hidden = self.file(".env", b"private")
        self.file("document.txt")
        organizer.organize(self.root, "extension", apply=True)
        organizer.undo(self.root, apply=True)
        self.assertEqual(nested.read_bytes(), b"nested")
        self.assertEqual(hidden.read_bytes(), b"private")

    def test_zero_size_file_is_not_a_directory(self):
        self.file("empty", b"")
        plan = organizer.organize(self.root, "size", apply=True)
        self.assertEqual(plan[0]["destination"], "Very Small (0-16 KB)/empty")

    def test_size_boundaries_are_exact(self):
        source = self.file("data.bin")
        cases = (
            (0, "Very Small (0-16 KB)"), (16 * 1024 - 1, "Very Small (0-16 KB)"),
            (16 * 1024, "Small (16 KB - 1 MB)"),
            (1024 ** 2 - 1, "Small (16 KB - 1 MB)"),
            (1024 ** 2, "Medium (1-128 MB)"),
            (128 * 1024 ** 2 - 1, "Medium (1-128 MB)"),
            (128 * 1024 ** 2, "Large (128 MB - 1 GB)"),
            (1024 ** 3 - 1, "Large (128 MB - 1 GB)"),
            (1024 ** 3, "Very Large (1 GB+)"),
        )
        # Mock only file size so tests do not allocate gigabytes.
        for size, expected in cases:
            with self.subTest(size=size), patch.object(Path, "stat") as get_stat:
                get_stat.return_value.st_size = size
                self.assertEqual(organizer.bucket_for(source, "size"), expected)

    def test_name_groups_and_punctuation(self):
        self.file("apple.txt")
        self.file("3.txt")
        self.file("!note.txt")
        organizer.organize(self.root, "name", apply=True)
        for relative in ("A/apple.txt", "3/3.txt", "Other/!note.txt"):
            self.assertTrue((self.root / relative).is_file())

    def test_extension_bucket_is_safe(self):
        self.assertEqual(organizer.bucket_for(Path("report.weird-ext"), "extension"), "No Extension")
        self.assertEqual(organizer.bucket_for(Path("report.PDF"), "extension"), "pdf")

    def test_destination_conflict_aborts_entire_plan(self):
        first = self.file("a.jpg", b"first")
        second = self.file("z.txt", b"second")
        existing = self.file("txt/z.txt", b"keep")
        with self.assertRaisesRegex(ValueError, "Destination already exists"):
            organizer.organize(self.root, "extension", apply=True)
        self.assertEqual(first.read_bytes(), b"first")
        self.assertEqual(second.read_bytes(), b"second")
        self.assertEqual(existing.read_bytes(), b"keep")
        self.assertFalse((self.root / organizer.JOURNAL).exists())

    def test_file_in_place_of_bucket_is_rejected(self):
        self.file("txt")
        self.file("document.txt")
        with self.assertRaisesRegex(ValueError, "folder is a file or link"):
            organizer.organize(self.root, "extension", apply=True)

    def test_existing_grouping_folder_is_retained(self):
        existing = self.file("txt/old.txt", b"old")
        self.file("new.txt", b"new")
        organizer.organize(self.root, "extension", apply=True)
        organizer.undo(self.root, apply=True)
        self.assertEqual(existing.read_bytes(), b"old")
        self.assertTrue(existing.parent.is_dir())

    def test_empty_preexisting_bucket_is_retained(self):
        (self.root / "txt").mkdir()
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        organizer.undo(self.root, apply=True)
        self.assertTrue((self.root / "txt").is_dir())

    def test_new_contents_are_retained_after_undo(self):
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        added = self.file("txt/added.txt", b"added later")
        organizer.undo(self.root, apply=True)
        self.assertEqual(added.read_bytes(), b"added later")
        self.assertTrue((self.root / "new.txt").exists())

    def test_second_operation_requires_undo(self):
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        with self.assertRaisesRegex(ValueError, "Run undo"):
            organizer.organize(self.root, "name", apply=True)

    def test_undo_preview_does_not_move(self):
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        plan = organizer.undo(self.root)
        self.assertEqual(plan, [{"source": "txt/new.txt", "destination": "new.txt"}])
        self.assertTrue((self.root / "txt/new.txt").exists())
        self.assertFalse((self.root / "new.txt").exists())

    def test_undo_without_record_does_not_flatten_folders(self):
        nested = self.file("folder/nested.txt")
        with self.assertRaisesRegex(ValueError, "No operation record"):
            organizer.undo(self.root, apply=True)
        self.assertTrue(nested.exists())

    def test_undo_collision_preflights_all_files(self):
        self.file("a.txt", b"first")
        self.file("z.txt", b"second")
        organizer.organize(self.root, "extension", apply=True)
        replacement = self.file("z.txt", b"replacement")
        with self.assertRaisesRegex(ValueError, "Undo conflict"):
            organizer.undo(self.root, apply=True)
        self.assertTrue((self.root / "txt/a.txt").exists())
        self.assertEqual(replacement.read_bytes(), b"replacement")
        self.assertEqual((self.root / "txt/z.txt").read_bytes(), b"second")

    def test_missing_recorded_file_is_rejected(self):
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        (self.root / "txt/new.txt").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            organizer.undo(self.root, apply=True)

    def test_partial_operation_can_be_undone(self):
        originals = {"a.txt": b"a", "b.txt": b"b"}
        for name, data in originals.items():
            self.file(name, data)
        real_move = organizer.move_exclusive
        count = 0

        def failing_move(source, destination):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("Simulated move failure")
            real_move(source, destination)

        with patch.object(organizer, "move_exclusive", side_effect=failing_move):
            with self.assertRaises(OSError):
                organizer.organize(self.root, "extension", apply=True)
        self.assertTrue((self.root / organizer.JOURNAL).exists())
        organizer.undo(self.root, apply=True)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, originals)

    def test_exclusive_move_does_not_replace_destination(self):
        source = self.file("source", b"source")
        destination = self.file("destination", b"destination")
        with self.assertRaises(FileExistsError):
            organizer.move_exclusive(source, destination)
        self.assertEqual(source.read_bytes(), b"source")
        self.assertEqual(destination.read_bytes(), b"destination")

    def test_interrupted_unlink_keeps_both_names(self):
        source = self.file("new.txt", b"preserve")
        with patch.object(Path, "unlink", side_effect=PermissionError("Simulated interruption")):
            with self.assertRaises(PermissionError):
                organizer.organize(self.root, "extension", apply=True)
        self.assertEqual(source.read_bytes(), b"preserve")
        self.assertEqual((self.root / "txt/new.txt").read_bytes(), b"preserve")
        with self.assertRaisesRegex(ValueError, "Undo conflict"):
            organizer.undo(self.root, apply=True)
        self.assertTrue((self.root / organizer.JOURNAL).exists())

    def test_unsupported_filesystem_preserves_files_and_can_undo(self):
        source = self.file("new.txt", b"preserve")
        with patch.object(organizer.os, "link", side_effect=OSError("Hard links unsupported")):
            with self.assertRaises(OSError):
                organizer.organize(self.root, "extension", apply=True)
        self.assertEqual(source.read_bytes(), b"preserve")
        organizer.undo(self.root, apply=True)
        self.assertEqual(list(self.root.iterdir()), [source])

    def test_journal_path_traversal_is_rejected(self):
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        journal = self.root / organizer.JOURNAL
        record = json.loads(journal.read_text(encoding="utf-8"))
        for invalid in ("../outside.txt", "/outside.txt", "C:/outside.txt", "txt/../new.txt"):
            record["moves"][0]["destination"] = invalid
            journal.write_text(json.dumps(record), encoding="utf-8")
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                organizer.undo(self.root, apply=True)
        self.assertTrue((self.root / "txt/new.txt").exists())

    def test_duplicate_records_are_rejected(self):
        self.file("new.txt")
        organizer.organize(self.root, "extension", apply=True)
        journal = self.root / organizer.JOURNAL
        record = json.loads(journal.read_text(encoding="utf-8"))
        record["moves"].append(record["moves"][0])
        journal.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            organizer.undo(self.root, apply=True)

    def test_symlinked_bucket_is_rejected(self):
        target = self.root / "target"
        target.mkdir()
        try:
            (self.root / "txt").symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable on this system")
        self.file("new.txt")
        with self.assertRaises(ValueError):
            organizer.organize(self.root, "extension", apply=True)

    def test_cli_is_preview_by_default(self):
        self.file("new.txt")
        code, stdout, stderr = self.cli(self.root)
        self.assertEqual((code, stderr), (0, ""))
        self.assertIn("Preview", stdout)
        self.assertTrue((self.root / "new.txt").exists())

    def test_cli_errors_are_readable(self):
        code, _, stderr = self.cli(self.root / "missing")
        self.assertEqual(code, 1)
        self.assertIn("Directory not found", stderr)

    def test_empty_interactive_path_is_rejected(self):
        with patch("builtins.input", return_value="  "):
            code, _, stderr = self.cli()
        self.assertEqual(code, 1)
        self.assertIn("path is required", stderr)

    def test_empty_folder_does_not_create_journal(self):
        self.assertEqual(organizer.organize(self.root, "extension", apply=True), [])
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
