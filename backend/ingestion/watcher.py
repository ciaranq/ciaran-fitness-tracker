import os, time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

INGEST_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "ingest"

class IngestHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and not event.src_path.endswith(".gitkeep"):
            print(f"[Watcher] New incoming file: {os.path.basename(event.src_path)}")

def start_watching():
    os.makedirs(INGEST_DIR, exist_ok=True)
    observer = Observer()
    observer.schedule(IngestHandler(), path=str(INGEST_DIR), recursive=False)
    observer.start()
    print(f"[Watcher] Monitoring {INGEST_DIR}...")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watching()
