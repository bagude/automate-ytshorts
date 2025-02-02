import sqlite3
import os


def fix_timestamps_path():
    story_id = "f366cc36-5d12-4235-b133-7558d8d8889c"
    story_dir = os.path.join("demo", "stories", story_id)

    # Find the UUID-based JSON file
    json_files = [f for f in os.listdir(
        story_dir) if f.endswith('.json') and f != 'audio.json']
    if not json_files:
        print("No UUID-based JSON file found")
        return

    json_path = os.path.join(story_dir, json_files[0])
    print(f"Found JSON file: {json_path}")

    # Update the database
    with sqlite3.connect("demo/story_pipeline.db") as conn:
        conn.execute(
            "UPDATE stories SET timestamps_path = ? WHERE id = ?",
            (json_path, story_id)
        )
        print("Updated database with correct path")


if __name__ == "__main__":
    fix_timestamps_path()
