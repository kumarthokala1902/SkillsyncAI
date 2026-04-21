import sqlite3
import os

db_path = 'instance/skillsync.db'

def patch():
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Checking mentor_booking schema...")
    cursor.execute("PRAGMA table_info(mentor_booking)")
    columns = [info[1] for info in cursor.fetchall()]

    if 'meeting_id' not in columns:
        print("Adding column 'meeting_id' to 'mentor_booking' table...")
        try:
            cursor.execute("ALTER TABLE mentor_booking ADD COLUMN meeting_id INTEGER REFERENCES mentor_booking_meeting(id)")
            conn.commit()
            print("Successfully added 'meeting_id' column.")
        except Exception as e:
            print(f"Error adding column: {e}")
    else:
        print("'meeting_id' column already exists.")

    conn.close()

if __name__ == "__main__":
    patch()
