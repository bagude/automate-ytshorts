import sqlite3


def fix_story_status():
    story_id = "f366cc36-5d12-4235-b133-7558d8d8889c"

    with sqlite3.connect("demo/story_pipeline.db") as conn:
        # First check current status
        cursor = conn.execute(
            "SELECT status FROM stories WHERE id = ?",
            (story_id,)
        )
        current_status = cursor.fetchone()[0]
        print(f"Current status: {current_status}")

        # Update to 'ready' status
        conn.execute(
            "UPDATE stories SET status = 'ready', error = NULL WHERE id = ?",
            (story_id,)
        )
        print("Updated status to 'ready'")

        # Verify the update
        cursor = conn.execute(
            "SELECT status FROM stories WHERE id = ?",
            (story_id,)
        )
        new_status = cursor.fetchone()[0]
        print(f"New status: {new_status}")


if __name__ == "__main__":
    fix_story_status()
