# -*- coding: utf-8 -*-
"""Tests for rumcore."""
import unittest
import os
import wcmatch.wcmatch as wcmatch
import shutil


# Below is general helper stuff that Python uses in unittests.  As these
# not meant for users, and could change without notice, include them
# ourselves so we aren't surprised later.
TESTFN = '@test'

# Disambiguate TESTFN for parallel testing, while letting it remain a valid
# module name.
TESTFN = "{}_{}_tmp".format(TESTFN, os.getpid())


def create_empty_file(filename):
    """Create an empty file. If the file already exists, truncate it."""

    fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    os.close(fd)


class TestWcmatch(unittest.TestCase):
    """Test the WcMatch class."""

    def mktemp(self, *parts):
        """Make temp directory."""

        filename = self.norm(*parts)
        base, file = os.path.split(filename)
        if not os.path.exists(base):
            os.makedirs(base)
        create_empty_file(filename)

    def norm(self, *parts):
        """Normalizes file path (in relation to temp dir)."""
        tempdir = os.fsencode(self.tempdir) if isinstance(parts[0], bytes) else self.tempdir
        return os.path.join(tempdir, *parts)

    def norm_list(self, files):
        """Normalize file list."""

        return [self.norm(x) for x in files]

    def setUp(self):
        """Setup."""

        self.tempdir = TESTFN + "_dir"
        self.mktemp('.hidden', 'a.txt')
        self.mktemp('.hidden', 'b.file')
        self.mktemp('.hidden_file')
        self.mktemp('a.txt')
        self.mktemp('b.file')
        self.mktemp('c.txt.bak')

        self.default_flags = wcmatch.R | wcmatch.I | wcmatch.M
        self.errors = []
        self.skipped = 0
        self.files = []

    def tearDown(self):
        """Cleanup."""

        shutil.rmtree(self.tempdir)

    def crawl_files(self, walker):
        """Crawl the files."""

        for f in walker.match():
            self.files.append(f)
        self.skipped = walker.get_skipped()

    def test_full_path_exclude(self):
        """Test full path exclude."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', '**/.hidden',
            True, True, self.default_flags | wcmatch.DIRPATHNAME | wcmatch.GLOBSTAR
        )

        self.crawl_files(walker)

        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_full_file(self):
        """Test full file."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '**/*.txt|-**/.hidden/*', None,
            True, True, self.default_flags | wcmatch.FILEPATHNAME | wcmatch.GLOBSTAR
        )

        self.crawl_files(walker)

        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_non_recursive(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', None,
            False, False, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_non_recursive_inverse(self):
        """Test non-recursive inverse search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.*|-*.file', None,
            False, False, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 2)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt', 'c.txt.bak']))

    def test_recursive(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', None,
            True, False, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_recursive_bytes(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            os.fsencode(self.tempdir),
            b'*.txt', None,
            True, False, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list([b'a.txt']))

    def test_recursive_hidden(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', None,
            True, True, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 4)
        self.assertEqual(sorted(self.files), self.norm_list(['.hidden/a.txt', 'a.txt']))

    def test_recursive_hidden_bytes(self):
        """Test non-recursive search with byte strings."""

        walker = wcmatch.WcMatch(
            os.fsencode(self.tempdir),
            b'*.txt', None,
            True, True, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 4)
        self.assertEqual(sorted(self.files), self.norm_list([b'.hidden/a.txt', b'a.txt']))

    def test_recursive_hidden_folder_exclude(self):
        """Test non-recursive search."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', '.hidden',
            True, True, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 3)
        self.assertEqual(sorted(self.files), self.norm_list(['a.txt']))

    def test_recursive_hidden_folder_exclude_inverse(self):
        """Test non-recursive search with inverse."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', '*|-.hidden',
            True, True, self.default_flags
        )

        self.crawl_files(walker)
        self.assertEqual(self.skipped, 4)
        self.assertEqual(sorted(self.files), self.norm_list(['.hidden/a.txt', 'a.txt']))

    def test_abort(self):
        """Test aborting."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt', None,
            True, True, self.default_flags
        )

        records = 0
        for f in walker.imatch():
            records += 1
            walker.kill()
        self.assertEqual(records, 1)

    def test_abort_early(self):
        """Test aborting early."""

        walker = wcmatch.WcMatch(
            self.tempdir,
            '*.txt*', None,
            True, True, self.default_flags
        )

        walker.kill()
        records = 0
        for f in walker.imatch():
            records += 1

        self.assertTrue(records == 1 or walker.get_skipped() == 1)
