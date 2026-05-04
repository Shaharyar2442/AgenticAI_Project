import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import pytest

def pytest_configure(config):
    """Ensure project root is on sys.path for all tests."""
    import sys
    root = os.path.dirname(__file__)
    if root not in sys.path:
        sys.path.insert(0, root)
