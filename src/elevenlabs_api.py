import os
import json
import base64
import requests
import sys
import csv
import uuid
from load_env import load_env
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def stream_raw_mp3(url, headers, payload, output_path):
    logging.info(f"Starting MP3 stream to {output_path}")
    try:
        with requests.post(url, headers=headers, json=payload, stream=True) as resp:
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
        logging.info(f"Successfully saved MP3 to {output_path}")
        return None
    except Exception as e:
        logging.error(f"MP3 stream failed: {str(e)}")
        raise


def stream_with_timestamps(url, headers, payload, output_path):
    """
    Collects *all* alignment chunks in a list, and writes audio bytes to output_path.
    """
    logging.info(f"Starting timestamped stream to {output_path}")
    alignment_data_list = []
    try:
        with requests.post(url, headers=headers, json=payload, stream=True) as resp:
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
        logging.info(f"Stream completed. Collected {len(alignment_data_list)} alignment chunks")
        return alignment_data_list if alignment_data_list else None
    except Exception as e:
        logging.error(f"Timestamped stream failed: {str(e)}")
        raise

def _make_headers(api_key):
    return {
        "xi-api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

def _make_payload(text):
    return {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128"
    }

def _handle_timestamps_mode(voice_id, headers, payload, mp3_path, json_folder):
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
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    stream_raw_mp3(url, headers, payload, mp3_path)
    return None

def _process_single_row(row, headers, voice_id, mp3_folder, json_folder, mode):
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
            json_id = _handle_default_mode(voice_id, headers, payload, mp3_path)

        return {
            **row,
            "output_mp3_path": mp3_path,
            "json_id": json_id if json_id else ""
        }
    except Exception as e:
        logging.error("Failed to process row '%s': %s", title, str(e))
        return {
            **row,
            "output_mp3_path": "ERROR",
            "json_id": "ERROR"
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
    """Processes CSV file through ElevenLabs API, adding generated audio metadata."""
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
        raise

def main():
    API_KEY = load_env("eleven-labs")[0]
    VOICE_ID = "kPzsL2i3teMYv0FxEYQ6"
    input_csv = "tifu_posts_try_one.csv"
    output_csv = "tifu_posts_output.csv"
    mode = "timestamps"
    process_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        api_key=API_KEY,
        voice_id=VOICE_ID,
        mode=mode,
        mp3_folder="demo/mp3",
        json_folder="demo/json"
    )

if __name__ == "__main__":
    main()
