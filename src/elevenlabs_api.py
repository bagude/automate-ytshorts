import os
import json
import base64
import requests
import sys
from load_env import load_env

def stream_raw_mp3(url, headers, payload, output_path):
    """
    Uses the standard streaming endpoint (no timestamps).
    Response is raw MP3 binary data.
    """
    with requests.post(url, headers=headers, json=payload, stream=True) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
    print(f"Audio saved to {output_path} (raw MP3 streaming)")

def stream_with_timestamps(url, headers, payload, output_path):
    """
    Uses the streaming endpoint that provides timestamps in JSON lines.
    Each line of the response is JSON with a base64-encoded MP3 chunk.
    """
    with requests.post(url, headers=headers, json=payload, stream=True) as resp:
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for line in resp.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    print("Received JSON chunk:", chunk)
                    
                    if "audio_base64" in chunk:
                        audio_bytes = base64.b64decode(chunk["audio_base64"])
                        f.write(audio_bytes)
                    else:
                        print("No 'audio_base64' in chunk.")
    print(f"Audio saved to {output_path}")


def main():
    # example orchestration of the Eleven Labs TTS Stream with Timestamps endpoint
    
    API_KEY = load_env("eleven-labs")[0]
    VOICE_ID = "kPzsL2i3teMYv0FxEYQ6"

    headers = {
        "xi-api-key": API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "text": (
            "Hello world! This is a test using the Eleven Labs TTS Stream with Timestamps endpoint. "
            "We are capturing character timing info and decoding the Base64 audio chunks."
        ),
        "model_id": "eleven_turbo_v2_5",
        "output_format": "mp3_44100_128"
    }

    # Choose which streaming option you want
    # Either "raw" (no timestamps) or "timestamps".
    mode = "timestamps" 
    output_path = "demo/mp3/output.mp3"

    if mode == "timestamps":
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream/with-timestamps"
        stream_with_timestamps(url, headers, payload, output_path)
    else:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
        stream_raw_mp3(url, headers, payload, output_path)


if __name__ == "__main__":
    main()
