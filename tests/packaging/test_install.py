"""Packaging and installation validation tests (D5.5)."""

import importlib
import importlib.metadata


def test_package_metadata() -> None:
    """Verify that neosentinel package can be imported and version can be read."""
    pkg = importlib.import_module("neosentinel")
    assert pkg is not None


def test_sdk_export() -> None:
    """Verify that core SDK symbols are available from neosentinel.engine."""
    from neosentinel.engine import ClusterConfig, PerformixTarget, SentinelEngine

    assert SentinelEngine is not None
    assert PerformixTarget is not None
    assert ClusterConfig is not None


def test_cli_entry_point() -> None:
    """Verify CLI main entry point is callable."""
    from neosentinel.cli.main import cli

    assert cli is not None
    assert callable(cli)
