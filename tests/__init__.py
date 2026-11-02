"""Test paketi. ULGEN modüllerinden ÖNCE geçici bir HOME ayarlanır; gerçek
~/ÜlgenVeri klasörüne asla dokunulmaz."""

import os
import tempfile

TEST_EV = tempfile.mkdtemp(prefix="ulgen-test-")
os.environ["HOME"] = TEST_EV
