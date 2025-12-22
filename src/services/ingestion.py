import time
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uuid
from src.clients.rabbitmq_client import RabbitMQClient
from src.clients.postgres_client import PostgresClient

PROCESSED_FILE = "processed_files.txt"


# -------------------------
# State helpers
# -------------------------

def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE, "r") as f:
        return set(line.strip() for line in f)


def mark_processed(path):
    with open(PROCESSED_FILE, "a") as f:
        f.write(path + "\n")


# -------------------------
# Bootstrap scan
# -------------------------

def scan_existing_files(path, processed, mq, db):
    for file in Path(path).glob("*.mp3"):
        file_path = str(file.resolve())
        if file_path not in processed:
            print(f"Found existing call: {file_path}")
            call_id = str(uuid.uuid4())
            mq.publish("transcription_jobs", {"file_path": file_path, "call_id": call_id})
            mark_processed(file_path)
            processed.add(file_path)
            db.create_call(file_path, call_id)


# -------------------------
# Watchdog handler
# -------------------------

class NewFileHandler(FileSystemEventHandler):
    def __init__(self, processed, MQClient: RabbitMQClient = None, DBClient: PostgresClient = None):
        self.processed = processed
        self.mq = MQClient
        self.db = DBClient

    def on_created(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith((".wav", ".mp3")):
            audio_path = str(Path(event.src_path).resolve())

            if audio_path in self.processed:
                return

            print(f"New call detected: {audio_path}")
            call_id = str(uuid.uuid4())
            self.mq.publish("transcription_jobs", {"file_path": audio_path, "call_id": call_id})
            mark_processed(audio_path)
            self.processed.add(audio_path)
            self.db.create_call(audio_path, call_id)


# -------------------------
# Main
# -------------------------

def main():
    mq = RabbitMQClient()
    db = PostgresClient()
    path = Path(
        "C:/Users/sugum/OneDrive/Documents/Projects/Zone24x7/english-contact-center-audio-dataset/qa-automation-poc/data"
    ).resolve()

    print(f"Watching directory: {path}")

    processed = load_processed()
    print(f"Loaded {len(processed)} processed files")


    scan_existing_files(path, processed, mq, db)

    event_handler = NewFileHandler(processed, mq, db)
    observer = Observer()
    observer.schedule(event_handler, str(path), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()


