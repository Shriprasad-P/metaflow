"""Test that S3 client works when current directory is not writeable."""

import importlib
import os
import tempfile

import pytest


def _mock_s3_dependencies(mocker):
    mock_boto3 = mocker.MagicMock()
    mock_transfer_config = mocker.MagicMock()
    mocker.patch.dict("sys.modules", {"boto3": mock_boto3})
    mocker.patch.dict(
        "sys.modules",
        {"boto3.s3.transfer": mocker.MagicMock(TransferConfig=mock_transfer_config)},
    )


def _load_s3_class():
    """Reload configuration and S3 so environment changes affect the default."""
    metaflow_config = importlib.import_module("metaflow.metaflow_config")
    s3_module = importlib.import_module("metaflow.plugins.datatools.s3.s3")
    importlib.reload(metaflow_config)
    importlib.reload(s3_module)
    # Keep the package-level export in sync for tests that import S3 later.
    s3_package = importlib.import_module("metaflow.plugins.datatools.s3")
    s3_package.S3 = s3_module.S3
    return s3_module.S3


def test_s3_client_readonly_cwd(mocker, monkeypatch):
    """Test that S3 client doesn't require writable CWD (issue #854)."""
    _mock_s3_dependencies(mocker)
    original_tempdir = os.environ.get("METAFLOW_TEMPDIR")

    try:
        with monkeypatch.context() as env:
            env.delenv("METAFLOW_TEMPDIR", raising=False)
            S3 = _load_s3_class()

            # Create a temporary read-only directory
            with tempfile.TemporaryDirectory() as tmpdir:
                readonly_dir = os.path.join(tmpdir, "readonly")
                os.makedirs(readonly_dir, mode=0o555)

                # Change to read-only directory
                original_cwd = os.getcwd()
                try:
                    os.chdir(readonly_dir)

                    # This should not raise an exception about permissions
                    # The S3 client should use system temp dir, not CWD
                    s3_client = S3()

                    # Verify that tmpdir was created in system temp, not CWD
                    assert s3_client._tmpdir is not None
                    # The temp dir should NOT be in the current (read-only) directory
                    assert not s3_client._tmpdir.startswith(readonly_dir)
                    # The temp dir should be in the system temp directory
                    system_temp = tempfile.gettempdir()
                    assert s3_client._tmpdir.startswith(system_temp)

                    # Clean up
                    s3_client.close()
                finally:
                    os.chdir(original_cwd)
                    # Make directory writable again so it can be deleted
                    os.chmod(readonly_dir, 0o755)
        assert os.environ.get("METAFLOW_TEMPDIR") == original_tempdir
    finally:
        # Restore the S3 module's import-time default after the isolated test.
        _load_s3_class()


def test_s3_client_respects_metaflow_tempdir(mocker, monkeypatch, tmp_path):
    """Test that METAFLOW_TEMPDIR overrides the system temporary directory."""
    _mock_s3_dependencies(mocker)
    configured_dir = tmp_path / "configured"
    configured_dir.mkdir()
    original_tempdir = os.environ.get("METAFLOW_TEMPDIR")

    try:
        with monkeypatch.context() as env:
            env.setenv("METAFLOW_TEMPDIR", str(configured_dir))
            S3 = _load_s3_class()

            s3_client = S3()
            try:
                assert s3_client._tmproot == str(configured_dir)
                assert os.path.dirname(s3_client._tmpdir) == str(configured_dir)
            finally:
                s3_client.close()
        assert os.environ.get("METAFLOW_TEMPDIR") == original_tempdir
    finally:
        # Restore the S3 module's import-time default after the isolated test.
        _load_s3_class()
