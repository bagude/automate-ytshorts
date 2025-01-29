import csv
import uuid
import os
import json
import base64
import logging

import requests
from src.load_env import load_env


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def stream_raw_mp3(url, headers, payload, output_path):
    """Stream and save raw MP3 audio from the API response.

    Args:
        url (str): API endpoint URL
        headers (dict): Request headers
        payload (dict): Request payload
        output_path (str): Path to save the MP3 file

    Returns:
        None
    """
    logging.info("Starting MP3 stream to %s", output_path)
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
        logging.info("Successfully saved MP3 to %s", output_path)
        return None
    except Exception as e:
        logging.error("MP3 stream failed: %s", str(e))
        raise


def stream_with_timestamps(url, headers, payload, output_path):
    """
    Collects *all* alignment chunks in a list, and writes audio bytes to output_path.
    Returns the alignment data list if successful, otherwise returns None.

    Args:
        url (str): API endpoint URL
        headers (dict): Request headers
        payload (dict): Request payload
        output_path (str): Path to save the MP3 file

    Returns:
        list: List of alignment data chunks
    """
    logging.info("Starting timestamped stream to %s", output_path)
    alignment_data_list = []
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        if "audio_base64" in chunk:
                            audio_bytes = base64.b64decode(chunk["audio_base64"])
                            f.write(audio_bytes)
                        if "alignment" in chunk and chunk["alignment"]:
                            alignment_data_list.append(chunk["alignment"])
        logging.info("Stream completed. Collected %d alignment chunks", len(alignment_data_list))
        return alignment_data_list if alignment_data_list else None
    except Exception as e:
        logging.error("Timestamped stream failed: %s", str(e))
        raise

def _make_headers(api_key):
    """Create headers for ElevenLabs API request.

    Args:
        api_key (str): ElevenLabs API key

    Returns:
        dict: Headers for API request
    """
    return {
        "xi-api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def _make_payload(text):
    """Create payload for ElevenLabs API request.

    Args:
        text (str): Text to be converted to speech

    Returns:
        dict: Payload for API request
    """
    return {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128"
    }

def _handle_timestamps_mode(voice_id, headers, payload, mp3_path, json_folder):
    """
    Handles the timestamps mode for ElevenLabs API.
    Returns the JSON ID if successful, otherwise returns None.

    Args:
        voice_id (str): ElevenLabs voice ID
        headers (dict): Request headers
        payload (dict): Request payload
        mp3_path (str): Path to save the MP3 file
        json_folder (str): Path to save the JSON file

    Returns:
        str: JSON ID if successful, otherwise None
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream/with-timestamps"
    alignment_data = stream_with_timestamps(url, headers, payload, mp3_path)
    
    if not alignment_data:
        logging.warning("No alignment data received for %s", mp3_path)
        return None

    json_id = str(uuid.uuid4())
    json_path = os.path.join(json_folder, f"{json_id}.json")
    with open(json_path, "w", encoding="utf-8") as jfile:
        json.dump(alignment_data, jfile)
    logging.debug("Saved alignment data to %s", json_path)
    
    return json_id

def _handle_default_mode(voice_id, headers, payload, mp3_path):
    """
    Handles the default mode for ElevenLabs API.
    Streams raw MP3 audio and saves it to the specified path.

    Args:
        voice_id (str): ElevenLabs voice ID
        headers (dict): Request headers
        payload (dict): Request payload
        mp3_path (str): Path to save the MP3 file

    Returns:
        None
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    stream_raw_mp3(url, headers, payload, mp3_path)

def _process_single_row(row, headers, voice_id, mp3_folder, json_folder, mode):
    """
    Processes a single row from the CSV file.
    Returns a dictionary with the processed row data.

    Args:
        row (dict): A single row from the CSV file
        headers (dict): Request headers
        voice_id (str): ElevenLabs voice ID
        mp3_folder (str): Path to save the MP3 file
        json_folder (str): Path to save the JSON file
        mode (str): Mode of operation ("timestamps" or "default")

    Returns:
        dict: Processed row data
    """
    text = row.get("Text", "")
    title = row.get("Title", "")
    
    logging.info("Processing row: %s", title)
    try:
        safe_title = title.replace(" ", "_").replace("/", "_")
        mp3_path = os.path.join(mp3_folder, f"{safe_title}.mp3")
        payload = _make_payload(text)

        if mode == "timestamps":
            json_id = _handle_timestamps_mode(voice_id, headers, payload, mp3_path, json_folder)
        else:
            _handle_default_mode(voice_id, headers, payload, mp3_path)
            json_id = None

        return {
            **row,
            "output_mp3_path": mp3_path,
            "json_id": json_id if json_id else ""
        }
    except (requests.RequestException, IOError, json.JSONDecodeError) as e:
        logging.error("Failed to process row '%s': %s", title, str(e))
        return {
            **row,
            "output_mp3_path": "ERROR",
            "json_id": f"ERROR: {str(e)}"
        }

def process_csv(
    input_csv_path,
    output_csv_path,
    api_key,
    voice_id,
    mode="timestamps",
    mp3_folder="demo/mp3",
    json_folder="demo/json"
):
    """
    Processes CSV file through ElevenLabs API, adding generated audio metadata.

    Args:
        input_csv_path (str): Path to the input CSV file
        output_csv_path (str): Path to save the output CSV file
        api_key (str): ElevenLabs API key
        voice_id (str): ElevenLabs voice ID
        mode (str): Mode of operation ("timestamps" or "default")
        mp3_folder (str): Path to save the MP3 files
        json_folder (str): Path to save the JSON files

    Returns:
        None
    """
    logging.info("Starting CSV processing")
    logging.debug("Input CSV: %s, Output CSV: %s", input_csv_path, output_csv_path)
    logging.debug("Mode: %s, MP3 folder: %s, JSON folder: %s", mode, mp3_folder, json_folder)
    
    os.makedirs(mp3_folder, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)
    headers = _make_headers(api_key)

    try:
        with open(input_csv_path, "r", encoding="utf-8", newline="") as fin, \
             open(output_csv_path, "w", encoding="utf-8", newline="") as fout:

            reader = csv.DictReader(fin)
            writer = csv.DictWriter(fout, fieldnames=reader.fieldnames + ["output_mp3_path", "json_id"])
            writer.writeheader()

            processed_count = 0
            for row in reader:
                processed_row = _process_single_row(row, headers, voice_id, mp3_folder, json_folder, mode)
                writer.writerow(processed_row)
                processed_count += 1
                if processed_count % 10 == 0:
                    logging.info("Processed %d rows", processed_count)

        logging.info("CSV processing completed successfully. Total rows: %d", processed_count)
        logging.info("Output CSV: %s", output_csv_path)
    except Exception as e:
        logging.critical("CSV processing failed: %s", str(e))
        # Don't raise the exception, just log it

def main():
    """Entry point for the ElevenLabs API processing script.
    
    Loads environment variables and processes a CSV file with default settings.
    """
    api_key = load_env("eleven-labs")[0]
    voice_id = "kPzsL2i3teMYv0FxEYQ6"
    input_csv = "tifu_posts_try_one.csv"
    output_csv = "tifu_posts_output.csv"
    mode = "timestamps"
    process_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        api_key=api_key,
        voice_id=voice_id,
        mode=mode,
        mp3_folder="demo/mp3",
        json_folder="demo/json"
    )

if __name__ == "__main__":
    main()
