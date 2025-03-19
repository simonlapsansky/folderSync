# One-Way Folder Synchronization Script

This script synchronizes files and directories from a source folder to a replica folder. It uses the `watchdog` library to monitor file system events and logs these events to a log file. The script can handle file creation, modification, deletion, and movement. Implemented and tested on Windows

## Features

- Synchronizes files and directories from a source folder to a replica folder.
- Synchronization based on the change log
- Synchronization based on recursive traversal of all folders
- Logs file system events to a log file.
- Handles file creation, modification, deletion, and movement.
- Supports synchronization intervals in seconds, minutes, or hours.

## Requirements

- Windows
- Python 3.x
- `watchdog` library

## Installation

1. Install the required library using pip:

    ```sh
    pip install watchdog
    ```

2. Save the script to a file, e.g., `sync.py`.

## Usage

Run the script with the following command:

```sh
python sync.py -s <source_folder> -r <replica_folder> -i <interval> -l <log_file> -u <unit>
```

### Arguments

- `-s`, `--source`: Source folder path.
- `-r`, `--replica`: Replica folder path.
- `-i`, `--interval`: Synchronization interval.
- `-l`, `--log_file`: Log file path.
- `-u`, `--unit`: Time unit for the interval (default: seconds). Choices are `seconds`, `minutes`, or `hours`.

### Example

```sh
python sync.py -s C:\path\to\source -r C:\path\to\replica -i 10 -l sync.log -u seconds
```

This command will synchronize the source folder to the replica folder every 10 seconds and log events to `sync.log`.

## Logging

The script logs events to two log files:

- `sync.log`: Main log file for synchronization operations.
- `sourceLog.log`: Log file for file system events used for synchronization.

## Implementation

### Event Handler
Create a class to handle file system events and log them using source_logger.

### Folder Synchronization
Define a function to synchronize files and directories from the source to the destination folder. This function copies new and modified files and removes files that are not in the source.

### Parse Event Log
Define a function to parse the event log and return a list of events.

### Handle Event
Define a function to handle a single event by performing the corresponding file operation (copy, delete, or move).

### Log-Based Synchronization
Define a function to synchronize files and directories based on the event log and clear the log file after synchronization.
