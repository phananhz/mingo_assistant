from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.app.lifecycle import SingleInstanceGuard


class AppLifecycleTests(unittest.TestCase):
    def test_second_guard_cannot_acquire_same_local_lock(self) -> None:
        with TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / ".instance.lock"
            first = SingleInstanceGuard(lock_path)
            second = SingleInstanceGuard(lock_path)
            try:
                self.assertTrue(first.acquire())
                self.assertFalse(second.acquire())
            finally:
                second.release()
                first.release()

            self.assertTrue(second.acquire())
            second.release()


if __name__ == "__main__":
    unittest.main()
