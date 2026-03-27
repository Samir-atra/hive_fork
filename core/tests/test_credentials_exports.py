import importlib
import sys
from unittest.mock import patch

import pytest


def test_broken_all_export_when_missing_deps():
    """
    Test that __all__ in core.framework.credentials does not contain
    optional components when their underlying dependencies are missing.
    """
    # Remove the module if it's already loaded to force reload
    if "framework.credentials" in sys.modules:
        del sys.modules["framework.credentials"]
    if "core.framework.credentials" in sys.modules:
        del sys.modules["core.framework.credentials"]

    # We will simulate missing dependencies by making the imports of .aden and .local fail
    # This matches the behavior when httpx or cryptography are not installed.
    # In python, we can simulate an ImportError during import of these submodules.

    # We patch builtins.__import__ to raise ImportError specifically for the .aden or .local modules
    # inside framework.credentials.
    original_import = __import__

    def mock_import(name, globals=None, locals=None, fromlist=(), level=0):
        # When importing .aden or .local inside framework.credentials
        if level > 0 and fromlist:
            if name == "aden" or name == "local":
                raise ImportError(f"No module named {name} (mocked)")
        return original_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=mock_import):
        import framework.credentials

        # Reloading it just to be sure
        importlib.reload(framework.credentials)

        assert hasattr(framework.credentials, "__all__")

        # Test that optional aden components are NOT in __all__
        aden_components = [
            "AdenCachedStorage",
            "AdenClientConfig",
            "AdenCredentialClient",
            "AdenSyncProvider",
        ]
        for comp in aden_components:
            assert comp not in framework.credentials.__all__, (
                f"{comp} should not be in __all__ when aden import fails"
            )

        # Test that optional local components are NOT in __all__
        local_components = [
            "LocalAccountInfo",
            "LocalCredentialRegistry",
        ]
        for comp in local_components:
            assert comp not in framework.credentials.__all__, (
                f"{comp} should not be in __all__ when local import fails"
            )

        # Base components should still be there
        assert "CredentialStore" in framework.credentials.__all__

        # Also, using 'from framework.credentials import *' should not crash.
        # This can be tested using exec
        exec_env = {}
        try:
            exec("from framework.credentials import *", exec_env)
        except AttributeError as e:
            pytest.fail(f"AttributeError raised during wildcard import: {e}")
