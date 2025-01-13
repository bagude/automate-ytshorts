import os
import json
import base64
import requests
import sys
import csv
import uuid
from load_env import load_env

def stream_raw_mp3(url, headers, payload, output_path):
    with requests.post(url, headers=headers, json=payload, stream=True) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
    return None

def stream_with_timestamps(url, headers, payload, output_path):
    """
    Collects *all* alignment chunks in a list, and writes audio bytes to output_path.
    """
    alignment_data_list = []
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
    # Return a list of all alignment chunks; None if empty
    return alignment_data_list if alignment_data_list else None

def process_csv(
    input_csv_path,
    output_csv_path,
    api_key,
    voice_id,
    mode="timestamps",
    mp3_folder="demo/mp3",
    json_folder="demo/json"
):
    os.makedirs(mp3_folder, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)

    headers = {
        "xi-api-key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    with open(input_csv_path, "r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames + ["output_mp3_path", "json_id"]
        with open(output_csv_path, "w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                text = row.get("Text", "")
                title = row.get("Title", "")

                payload = {
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "output_format": "mp3_44100_128"
                }

                safe_title = title.replace(" ", "_").replace("/", "_")
                mp3_filename = f"{safe_title}.mp3"
                mp3_path = os.path.join(mp3_folder, mp3_filename)

                if mode == "timestamps":
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream/with-timestamps"
                    alignment_data_list = stream_with_timestamps(url, headers, payload, mp3_path)
                    
                    if alignment_data_list:
                        json_id = str(uuid.uuid4())
                        json_path = os.path.join(json_folder, f"{json_id}.json")
                        with open(json_path, "w", encoding="utf-8") as jfile:
                            json.dump(alignment_data_list, jfile)
                        row["json_id"] = json_id
                    else:
                        print("Warning: alignment_data_list is None or empty")
                        row["json_id"] = ""
                else:
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
                    _ = stream_raw_mp3(url, headers, payload, mp3_path)
                    row["json_id"] = ""

                row["output_mp3_path"] = mp3_path
                writer.writerow(row)
                sys.exit()

    print(f"Done. Output CSV: {output_csv_path}")

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
