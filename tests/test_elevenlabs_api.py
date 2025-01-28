import pytest
from unittest.mock import patch, Mock
import os
import csv
import json
import uuid
from src.elevenlabs_api import process_csv, stream_raw_mp3, stream_with_timestamps

@pytest.fixture
def mock_csv_content():
    return """Title,Text
Test Post 1,This is some sample text
Test Post 2,Another piece of content here
"""

@pytest.fixture
def tmp_csv(tmp_path, mock_csv_content):
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(mock_csv_content)
    return csv_path

@pytest.fixture
def mock_api_success():
    mock_resp = Mock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.__enter__ = Mock(return_value=mock_resp)
    mock_resp.__exit__ = Mock(return_value=None)
    mock_resp.iter_content.side_effect = [[b"fake", b"mp3", b"data"]] * 2  # Return same data for both calls
    mock_resp.iter_lines.side_effect = [[
        json.dumps({"audio_base64": "ZmFrZQ==", "alignment": {"chunk": "1"}}).encode(),
        json.dumps({"audio_base64": "ZmFrZQ==", "alignment": {"chunk": "2"}}).encode()
    ]] * 2  # Return two chunks for both calls
    return mock_resp

class TestElevenLabsAPI:
    @patch("requests.post")
    def test_process_csv_success(self, mock_post, tmp_path, tmp_csv, mock_api_success):
        mock_post.return_value = mock_api_success
        output_csv = tmp_path / "output.csv"
        
        process_csv(
            input_csv_path=str(tmp_csv),
            output_csv_path=str(output_csv),
            api_key="fake-api-key",
            voice_id="test-voice",
            mp3_folder=str(tmp_path / "mp3"),
            json_folder=str(tmp_path / "json")
        )

        # Verify CSV output
        with open(output_csv) as f:
            rows = list(csv.DictReader(f))
            assert len(rows) == 2
            assert all(row["output_mp3_path"] != "ERROR" for row in rows)
            
        # Verify MP3 files created
        mp3_dir = tmp_path / "mp3"
        assert len(list(mp3_dir.glob("*.mp3"))) == 2
        
        # Verify JSON files created in timestamps mode
        json_dir = tmp_path / "json"
        assert len(list(json_dir.glob("*.json"))) == 2

    @patch("requests.post")
    def test_process_csv_error_handling(self, mock_post, tmp_path, tmp_csv):
        mock_post.side_effect = Exception("API failure")
        output_csv = tmp_path / "output.csv"

        process_csv(
            input_csv_path=str(tmp_csv),
            output_csv_path=str(output_csv),
            api_key="fake-api-key",
            voice_id="test-voice",
            mp3_folder=str(tmp_path / "mp3"),
            json_folder=str(tmp_path / "json")
        )

        with open(output_csv) as f:
            rows = list(csv.DictReader(f))
            assert all(row["output_mp3_path"] == "ERROR" for row in rows)

    @patch("requests.post")
    def test_stream_raw_mp3_success(self, mock_post, mock_api_success, tmp_path):
        mock_post.return_value = mock_api_success
        test_path = tmp_path / "test.mp3"
        
        result = stream_raw_mp3(
            url="http://fake-api.com",
            headers={"xi-api-key": "fake"},
            payload={"text": "test"},
            output_path=str(test_path)
        )
        
        assert test_path.exists()
        assert test_path.stat().st_size > 0

    @patch("requests.post")
    def test_stream_with_timestamps(self, mock_post, mock_api_success, tmp_path):
        mock_post.return_value = mock_api_success
        test_path = tmp_path / "test.mp3"
        
        result = stream_with_timestamps(
            url="http://fake-api.com",
            headers={"xi-api-key": "fake"},
            payload={"text": "test"},
            output_path=str(test_path)
        )
        
        assert isinstance(result, list)
        assert len(result) == 2  # Two chunks from mock response
        assert test_path.exists()

    def test_directory_creation(self, tmp_path):
        # Create dummy input file first
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("Title,Text\nTest,Content")
        
        # Then test processing
        process_csv(
            input_csv_path=str(input_csv),
            output_csv_path=str(tmp_path / "output.csv"),
            api_key="fake",
            voice_id="test",
            mp3_folder=str(tmp_path / "mp3"),
            json_folder=str(tmp_path / "json")
        )
        
        assert (tmp_path / "mp3").exists()
        assert (tmp_path / "json").exists() 