import os
from pathlib import Path
import tempfile
import unittest

from scripts.local_key_setup import load_key, save_key


@unittest.skipUnless(os.name == "nt", "Windows DPAPI integration")
class LocalKeyHandoffTests(unittest.TestCase):
    def test_windows_encrypted_round_trip_never_writes_plaintext(self):
        fake = "sk-FAKE-LOCAL-UNIT-TEST-ONLY-12345"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "key.dpapi"
            save_key(fake, path)
            self.assertNotIn(fake.encode(), path.read_bytes())
            self.assertEqual(load_key(path), fake)

    def test_invalid_key_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "key.dpapi"
            for invalid in ("", "short", "secret with spaces", "x\nprivate"):
                with self.assertRaises(ValueError): save_key(invalid, path)
                self.assertFalse(path.exists())

    def test_corrupted_or_missing_ciphertext_has_safe_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "key.dpapi"
            with self.assertRaisesRegex(ValueError, "No usable local key"):
                load_key(path)
            path.write_bytes(b"invalid-ciphertext")
            with self.assertRaisesRegex(ValueError, "No usable local key"):
                load_key(path)
