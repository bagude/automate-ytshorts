import pytest
from unittest.mock import patch
from src.run_pipeline import Pipeline
import os

@pytest.mark.parametrize("platform, env_vars, expected", [
    ('youtube-shorts', {'YT_USERNAME': 'test_user', 'YT_PASSWORD': 'test_pass'}, ('test_user', 'test_pass')),
    ('youtube-shorts', {'YT_USERNAME': '', 'YT_PASSWORD': 'test_pass'}, ('', 'test_pass')),
    ('youtube-shorts', {'YT_USERNAME': 'test_user', 'YT_PASSWORD': ''}, ('test_user', '')),
    ('youtube-shorts', {'YT_USERNAME': '', 'YT_PASSWORD': ''}, ('', '')),
    ('other-platform', {'YT_USERNAME': 'test_user', 'YT_PASSWORD': 'test_pass'}, (None, None)),
])
def test_load_env(platform, env_vars, expected, mocker):
    env_vars = {k: v if v is not None else '' for k, v in env_vars.items()}
    mocker.patch.dict(os.environ, env_vars)
    pipeline = Pipeline(platform=platform, video_fp='path/to/video.mp4')
    assert pipeline.load_env() == expected