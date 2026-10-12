import os
import tempfile
import unittest
from pathlib import Path

from deploy.scripts.backup_check import check_directory


class BackupFreshnessTest(unittest.TestCase):
    def test_missing_and_stale_archives_fail(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertFalse(check_directory(root, '*.age', now=200000)['healthy'])
            path=Path(root)/'synthetic.age'
            path.write_bytes(b'age-encryption.org/v1\nsynthetic test envelope, not an encrypted archive\n')
            path.chmod(0o600)
            os.utime(path,(1,1))
            self.assertFalse(check_directory(root,'*.age',now=200000)['healthy'])
            os.utime(path,(199000,199000))
            self.assertTrue(check_directory(root,'*.age',now=200000)['healthy'])

    def test_plaintext_permissions_future_time_and_symlinks_fail(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'synthetic.age'
            path.write_bytes(b'plaintext does not become encrypted through a filename')
            path.chmod(0o600)
            self.assertFalse(check_directory(root,'*.age')['healthy'])
            path.write_bytes(b'age-encryption.org/v1\nsynthetic\n')
            path.chmod(0o644)
            self.assertFalse(check_directory(root,'*.age')['healthy'])
            path.chmod(0o600)
            os.utime(path,(200000,200000))
            self.assertFalse(check_directory(root,'*.age',now=1000)['healthy'])
            os.utime(path,(900,900))
            link=Path(root)/'link.age';link.symlink_to(path)
            result=check_directory(root,'*.age',now=1000)
            self.assertFalse(result['healthy']);self.assertEqual(result['invalid_archives'],1)
            self.assertNotIn(str(path),str(result))
