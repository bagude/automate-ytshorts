import json
import whisper
import logging
import os
from typing import Dict, Optional, Union, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def _get_json_path(audio_path: str, json_folder: str = "demo/json") -> str:
    """Generate JSON output path based on audio file name.

    Args:
        audio_path (str): Path to the audio file
        json_folder (str): Folder to save JSON files. Defaults to "demo/json"

    Returns:
        str: Path where the JSON file should be saved
    """
    # Create json folder if it doesn't exist
    os.makedirs(json_folder, exist_ok=True)

    # Get the base name of the audio file without extension
    base_name = os.path.splitext(os.path.basename(audio_path))[0]

    # Create json path
    return os.path.join(json_folder, f"{base_name}.json")


def load_whisper_model(model_name: str = "base") -> whisper.Whisper:
    """Load the Whisper model.

    Args:
        model_name (str): Name of the Whisper model to load. Defaults to "base".
                         Options: ["tiny", "base", "small", "medium", "large"]

    Returns:
        whisper.Whisper: Loaded Whisper model

    Raises:
        ValueError: If model_name is not valid
        RuntimeError: If model loading fails
    """
    try:
        logging.info("Loading Whisper model: %s", model_name)
        model = whisper.load_model(model_name, device="cpu")
        logging.info("Successfully loaded Whisper model")
        return model
    except Exception as e:
        logging.error("Failed to load Whisper model: %s", str(e))
        raise RuntimeError(f"Failed to load Whisper model: {str(e)}")


def transcribe_audio(
    audio_path: Union[str, Path],
    model: str = "base",
    verbose: bool = False,
    temperature: float = 0,
    compression_ratio_threshold: float = 2.4,
    logprob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    condition_on_previous_text: bool = True,
    initial_prompt: Optional[str] = None,
    word_timestamps: bool = False,
    prepend_punctuations: str = "'\"({[",
    append_punctuations: str = "'\",.!?:)}]",
    fp16: bool = True
) -> Dict[str, Any]:
    """Transcribe audio using Whisper API.

    Args:
        audio_path: Path to the audio file
        model: Whisper model to use
        verbose: Whether to print debug information
        temperature: Temperature for sampling
        compression_ratio_threshold: Compression ratio threshold
        logprob_threshold: Log probability threshold
        no_speech_threshold: No speech threshold
        condition_on_previous_text: Whether to condition on previous text
        initial_prompt: Initial prompt for transcription
        word_timestamps: Whether to include word timestamps
        prepend_punctuations: Punctuations to prepend
        append_punctuations: Punctuations to append
        fp16: Whether to use FP16

    Returns:
        Dict[str, Any]: Transcription result containing text and metadata
    """
    try:
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logging.info("Starting transcription of: %s", audio_path)

        # Load model if not provided
        if model is None:
            model = load_whisper_model(model_name)

        # Perform transcription
        result = model.transcribe(
            audio_path,
            verbose=verbose,
            fp16=fp16
        )

        # Generate and save JSON output
        output_json = _get_json_path(audio_path, json_folder)
        logging.info("Saving transcription to: %s", output_json)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logging.info("Transcription completed successfully")
        return result

    except Exception as e:
        logging.error("Transcription failed: %s", str(e))
        raise RuntimeError(f"Transcription failed: {str(e)}")


def main() -> None:
    """Entry point for the Whisper API transcription script."""
    try:
        # Example usage
        audio_path = r'demo\mp3\TIFU_by_correcting_my_manager_on_a_phrase_she_was_using.mp3'

        result = transcribe_audio(
            audio_path=audio_path,
            verbose=True,
            fp16=False
        )

        logging.info("Transcribed text: %s", result["text"][:100] + "...")

    except Exception as e:
        logging.error("Main execution failed: %s", str(e))
        raise


if __name__ == "__main__":
    main()
