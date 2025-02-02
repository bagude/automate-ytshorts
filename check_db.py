import sqlite3


def check_story():
    with sqlite3.connect("demo/story_pipeline.db") as conn:
        cursor = conn.execute(
            "SELECT id, timestamps_path, audio_path, status FROM stories WHERE id=?",
            ("f366cc36-5d12-4235-b133-7558d8d8889c",)
        )
        row = cursor.fetchone()
        if row:
            print(f"Story ID: {row[0]}")
            print(f"Timestamps path: {row[1]}")
            print(f"Audio path: {row[2]}")
            print(f"Status: {row[3]}")
        else:
            print("Story not found")


if __name__ == "__main__":
    check_story()
