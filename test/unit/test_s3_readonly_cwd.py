"""Test that S3 client works when current directory is not writeable."""

import os
import tempfile
import pytest


def test_s3_client_readonly_cwd(mocker):
    """Test that S3 client doesn't require writable CWD (issue #854)."""
    # Mock boto3 and dependencies before importing S3
    mock_boto3 = mocker.MagicMock()
    mock_transfer_config = mocker.MagicMock()
    mocker.patch.dict("sys.modules", {"boto3": mock_boto3})
    mocker.patch.dict(
        "sys.modules",
        {"boto3.s3.transfer": mocker.MagicMock(TransferConfig=mock_transfer_config)},
    )

    from metaflow.plugins.datatools.s3 import S3

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
