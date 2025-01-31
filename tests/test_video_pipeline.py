import os
import pytest
from src.video_pipeline import InputValidator


class TestInputValidator:
    @pytest.fixture
    def validator(self):
        """Creates an InputValidator instance for testing."""
        return InputValidator()

    @pytest.fixture
    def tmp_files(self, tmp_path):
        """Creates temporary files for testing."""
        # Create test files
        tts_file = tmp_path / "test_tts.mp3"
        music_file = tmp_path / "test_music.mp3"
        video_file = tmp_path / "test_video.mp4"

        # Create empty files
        tts_file.write_text("")
        music_file.write_text("")
        video_file.write_text("")

        return {
            "tts": str(tts_file),
            "music": str(music_file),
            "video": str(video_file),
            "output": str(tmp_path / "output.mp4")
        }

    def test_validate_inputs_success(self, validator, tmp_files):
        """Test successful validation of all input files."""
        validator.validate_inputs(
            tmp_files["output"],
            tmp_files["tts"],
            tmp_files["music"],
            tmp_files["video"]
        )

    def test_validate_inputs_missing_file(self, validator, tmp_files):
        """Test validation with missing input file."""
        os.remove(tmp_files["tts"])
        with pytest.raises(FileNotFoundError, match="TTS file not found"):
            validator.validate_inputs(
                tmp_files["output"],
                tmp_files["tts"],
                tmp_files["music"],
                tmp_files["video"]
            )

    def test_validate_inputs_invalid_output_dir(self, validator, tmp_files):
        """Test validation with non-existent output directory."""
        invalid_output = "/nonexistent/dir/output.mp4"
        with pytest.raises(FileNotFoundError, match="Output directory not found"):
            validator.validate_inputs(
                invalid_output,
                tmp_files["tts"],
                tmp_files["music"],
                tmp_files["video"]
            )

    def test_validate_durations_success(self, validator):
        """Test successful duration validation."""
        validator.validate_durations(audio_duration=10.0, video_duration=20.0)

    def test_validate_durations_audio_too_long(self, validator):
        """Test duration validation when audio is longer than video."""
        with pytest.raises(ValueError, match="Audio duration .* exceeds video duration"):
            validator.validate_durations(
                audio_duration=20.0, video_duration=10.0)

    def test_validate_durations_equal(self, validator):
        """Test duration validation with equal durations."""
        validator.validate_durations(audio_duration=10.0, video_duration=10.0)
