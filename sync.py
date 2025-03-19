import hashlib
import argparse
import logging
import time
import os
import shutil
import stat
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re


def remove_readonly(func, path, _):
    "Clear the readonly bit and reattempt the removal upon failure due to permissions"
    os.chmod(path, stat.S_IWRITE)
    func(path)


def convert_interval(interval, unit):
    """Convert the interval to seconds based on the unit."""
    if unit == "seconds":
        return interval
    elif unit == "minutes":
        return interval * 60
    elif unit == "hours":
        return interval * 3600
    else:
        raise ValueError("Invalid time unit. "
                         "Use 'seconds', 'minutes', or 'hours'.")


class SyncEventHandler(FileSystemEventHandler):
    """Event handler for file system changes."""
    def __init__(self, source_logger):
        self.source_logger = source_logger

    def log_event(self, event):
        """Log the file system event to the source log file and terminal."""
        # Log the rename of the file or directory
        if event.event_type == "moved":
            log_message_deleted = f"Event type: deleted: {event.src_path}"
            log_message_moved = f"Event type: {event.event_type}: {event.dest_path}"
            self.source_logger.info(log_message_deleted)
            self.source_logger.info(log_message_moved)
        else:
            log_message = f"Event type: {event.event_type}: {event.src_path}"
            self.source_logger.info(log_message)

    def on_moved(self, event):
        """Handle moved file system event."""
        self.log_event(event)

    def on_deleted(self, event):
        """Handle deleted file system event."""
        self.log_event(event)

    def on_created(self, event):
        """Handle created file system event."""
        self.log_event(event)

    def on_modified(self, event):
        """Handle modified file system event."""
        self.log_event(event)


def calculate_md5(file_path, main_logger):
    """Calculate the MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        main_logger.error(f"Error calculating MD5 for {file_path}: {e}")
        return None


def sync_folders(src, dest, log_file, main_logger):
    """Synchronize files and directories from source to destination."""
    if not os.path.exists(dest):
        os.makedirs(dest)

    sourceFiles = set(os.listdir(src))
    replicaFiles = set(os.listdir(dest))

    # Copy new and modified files from src to dest
    for item in sourceFiles:
        src_item_path = os.path.join(src, item)
        dest_item_path = os.path.join(dest, item)

        if os.path.isdir(src_item_path):
            sync_folders(src_item_path, dest_item_path, log_file, main_logger)
        else:
            if not os.path.exists(dest_item_path) or calculate_md5(src_item_path, main_logger) != calculate_md5(dest_item_path, main_logger):
                try:
                    shutil.copy2(src_item_path, dest_item_path)
                    main_logger.info(f"Copied: {src_item_path} to {dest_item_path}")
                    print(f"Copied: {src_item_path} to {dest_item_path}")
                except Exception as e:
                    main_logger.error(f"Error copying {src_item_path} to {dest_item_path}: {e}")

    # Remove files from dest that are not in src
    for item in replicaFiles - sourceFiles:
        dest_item_path = os.path.join(dest, item)
        try:
            if os.path.isdir(dest_item_path):
                shutil.rmtree(dest_item_path, onerror=remove_readonly)
                main_logger.info(f"Removed directory: {dest_item_path}")
                print(f"Removed directory: {dest_item_path}")
            else:
                os.remove(dest_item_path)
                main_logger.info(f"Removed file: {dest_item_path}")
                print(f"Removed file: {dest_item_path}")
        except Exception as e:
            main_logger.error(f"Error removing {dest_item_path}: {e}")


def parse_event_log(log_file, main_logger):
    """Parse the event log and return a list of events."""
    events = []
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                match = re.search(r'Event type: (.+?): (.+)', line)
                if match:
                    event_type = match.group(1)
                    item_path = match.group(2)
                    events.append((event_type, item_path))
    except Exception as e:
        main_logger.error(f"Error reading log file {log_file}: {e}")
    return events


def handle_event(event, src, dest, main_logger):
    """Handle a single event by performing the corresponding file operation."""
    event_type, src_item_path = event
    dest_item_path = os.path.join(dest, os.path.relpath(src_item_path, src))

    try:
        if event_type == "deleted":
            if os.path.isdir(dest_item_path):
                if os.path.exists(dest_item_path):
                    shutil.rmtree(dest_item_path, onerror=remove_readonly)
                    main_logger.info(f"Removed directory: {dest_item_path}")
                    print(f"Removed directory: {dest_item_path}")
            else:
                if os.path.exists(dest_item_path):
                    os.remove(dest_item_path)
                    main_logger.info(f"Removed file: {dest_item_path}")
                    print(f"Removed file: {dest_item_path}")
        elif event_type in ["created", "modified", "moved"]:
            if os.path.isdir(src_item_path):
                if os.path.exists(src_item_path):
                    if not os.path.exists(dest_item_path):
                        shutil.copytree(src_item_path, dest_item_path)
                        main_logger.info(f"Copied directory: {src_item_path} to {dest_item_path}")
                        print(f"Copied directory: {src_item_path} to {dest_item_path}")
            else:
                if os.path.exists(src_item_path):
                    if not os.path.exists(dest_item_path) or calculate_md5(src_item_path, main_logger) != calculate_md5(dest_item_path, main_logger):
                        shutil.copy2(src_item_path, dest_item_path)
                        main_logger.info(f"Copied file: {src_item_path} to {dest_item_path}")
                        print(f"Copied file: {src_item_path} to {dest_item_path}")
    except Exception as e:
        main_logger.error(f"Error handling event {event}: {e}")


def sync_from_log(src, dest, source_log_file, main_logger):
    """Synchronize files and directories based on the event log."""
    events = parse_event_log(source_log_file, main_logger)
    for event in events:
        handle_event(event, src, dest, main_logger)

    # Clear the source log file after synchronization
    with open('sourceLog.log', "w") as f:
        f.truncate()


def main():
    parser = argparse.ArgumentParser(description="One-way folder synchronization script.")
    parser.add_argument("-s", "--source", help="Source folder path")
    parser.add_argument("-r", "--replica", help="Replica folder path")
    parser.add_argument("-i", "--interval", type=int, help="Synchronization interval")
    parser.add_argument("-l", "--log_file", help="Log file path")
    parser.add_argument("-u", "--unit", choices=["seconds", "minutes", "hours"], default="seconds",
                        help="Time unit for the interval (default: seconds)")
    args = parser.parse_args()

    # Convert the interval to seconds
    args.interval = convert_interval(args.interval, args.unit)

    # Create a logger for the main log file
    main_logger = logging.getLogger('mainLog')
    main_logger.setLevel(logging.INFO)
    main_handler = logging.FileHandler(args.log_file)
    main_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    main_logger.addHandler(main_handler)

    # Create a new logger for sourceLog
    source_logger = logging.getLogger('sourceLog')
    source_logger.setLevel(logging.INFO)
    source_handler = logging.FileHandler('sourceLog.log')
    source_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    source_logger.addHandler(source_handler)
    source_log_file = source_logger.handlers[0].baseFilename

    event_handler = SyncEventHandler(source_logger)
    observer = Observer()
    observer.schedule(event_handler, path=args.source, recursive=True)
    observer.start()

    try:
        # Clear the source log file at the start
        with open('sourceLog.log', "w") as f:
            f.truncate()

        while True:
            # Check if there are any events logged in the source log file
            if os.path.getsize('sourceLog.log') > 0:
                main_logger.info("Synchronizing from log...")
                sync_from_log(args.source, args.replica, source_log_file, main_logger)
            else:
                main_logger.info("Synchronizing from source...")
                sync_folders(args.source, args.replica, args.log_file, main_logger)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
