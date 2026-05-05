import pytest


@pytest.fixture(autouse=True)
def temp_media_root(settings, tmp_path):
    """Store uploaded test files outside the repository worktree."""
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_URL = "/media/"
