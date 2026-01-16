# Android Backup Buddy

A CLI tool for IT technicians to automate Android device diagnostics and secure backups.

## Features

- **Device Detection**: Automatically detects connected Android devices via ADB.
- **Diagnostics**: Generates reports on device model, Android version, battery status, and storage usage.
- **Secure Backup**: Pulls data from the device, creates a zip archive, and encrypts it with AES-256.
- **Cross-Platform**: Built with Python, runs on Linux, Windows, and macOS.

## Prerequisites

- Python 3.x
- ADB (Android Debug Bridge) installed and added to your system PATH.
- Android device with USB debugging enabled.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd "Android Backup Buddy"
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Interactive Mode (Recommended)
Simply run the tool without arguments to enter the interactive menu:
```bash
python main.py
```
Follow the on-screen prompts to:
1.  **Detect Devices**: Select "1" to search for connected Android devices.
2.  **Select Device**: If multiple devices are found, choose one from the list.
3.  **Device Menu**:
    *   **1. Device Report**: Generates and displays a diagnostics report (saved in `reports/` folder).
    *   **2. Device Backup**: Choose between "Pic Only" (/sdcard/DCIM) or "All Data" (/sdcard) to backup and encrypt.
    *   **3. Restore Backup**: Restore a backup (.enc or .zip) to the device.
    *   **4. Developer Options**: Decrypt an existing encrypted backup for manual inspection.

### Advanced Usage (CLI Flags)
You can still use command-line arguments for automation or scripts.

**Detect Devices**
```bash
python main.py --detect
```

**Run Diagnostics**
```bash
python main.py --diagnose [--device-id <DEVICE_ID>]
```

**Perform Secure Backup**
```bash
python main.py --backup [--device-id <DEVICE_ID>] [--source <REMOTE_PATH>] [--dest <LOCAL_FOLDER>]
```

## Packaging as Executable

You can package this tool as a standalone executable using `PyInstaller`.

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build the executable:
   ```bash
   pyinstaller --onefile --name android-backup-buddy main.py
   ```

3. The executable will be found in the `dist/` directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
