import argparse
import logging
import sys
from detector import get_connected_devices
from diagnostics import Diagnostics
from backup import BackupManager

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def interactive_mode():
    while True:
        print("\n=== Android Backup Buddy ===")
        print("1. Detect Device")
        print("0. Close")
        
        choice = input("Select an option: ").strip()
        
        if choice == '0':
            print("Goodbye!")
            sys.exit(0)
        elif choice == '1':
            devices = get_connected_devices()
            if not devices:
                print("No devices found.")
                continue
            
            selected_device = None
            if len(devices) == 1:
                selected_device = devices[0]['id']
                print(f"Device detected: {selected_device}")
            else:
                print("\nMultiple devices found:")
                for idx, d in enumerate(devices):
                    print(f"{idx + 1}. {d['id']} ({d['status']})")
                
                try:
                    sel = int(input("Select device number: "))
                    if 1 <= sel <= len(devices):
                        selected_device = devices[sel-1]['id']
                    else:
                        print("Invalid selection.")
                        continue
                except ValueError:
                    print("Invalid input.")
                    continue
            
            # Secondary Menu
            while True:
                print(f"\n--- Menu for {selected_device} ---")
                print("1. Device Report")
                print("2. Device Backup")
                print("3. Restore Backup")
                print("4. Developer Options (Decrypt Backup)")
                print("0. Back to Main Menu")
                
                sub_choice = input("Select an option: ").strip()
                
                if sub_choice == '0':
                    break
                elif sub_choice == '1':
                    # Report
                    print("Generating report...")
                    diag = Diagnostics(selected_device)
                    # Use default 'reports' folder logic in diagnostics.py
                    path = diag.generate_report()
                    if path:
                        print(f"Report saved: {path}")
                        print("--- Report Content ---")
                        try:
                            with open(path, 'r') as f:
                                print(f.read())
                        except:
                            pass
                        print("----------------------")
                elif sub_choice == '2':
                    # Backup
                    print("\n--- Backup Selection ---")
                    print("1. Pic Only (Backs up /sdcard/DCIM)")
                    print("2. All Data (Backs up /sdcard)")
                    print("3. Contacts (Text Dump)")
                    print("4. SMS (Text Dump)")
                    
                    bk_choice = input("Select backup type: ").strip()
                    source = None
                    
                    if bk_choice == '1':
                        source = "/sdcard/DCIM"
                    elif bk_choice == '2':
                        source = "/sdcard"
                    elif bk_choice == '3':
                        print("Backing up contacts...")
                        bm = BackupManager(selected_device)
                        res = bm.backup_contacts() # Defaults to backups/contacts
                        if res:
                            print(f"Contacts Backup Complete! File: {res}")
                        else:
                            print("Contacts Backup failed.")
                        continue # Skip the general source logic
                    elif bk_choice == '4':
                        print("Backing up SMS...")
                        bm = BackupManager(selected_device)
                        res = bm.backup_sms() # Defaults to backups/messages
                        if res:
                            print(f"SMS Backup Complete! File: {res}")
                        else:
                            print("SMS Backup failed.")
                        continue
                    
                    if source:
                        print(f"Starting backup of {source}...")
                        bm = BackupManager(selected_device)
                        res = bm.backup_device(source, "backups")
                        if res:
                            print(f"Backup Complete! File: {res}")
                            print("Encryption key 'backup_key.key' is in the current directory.")
                        else:
                            print("Backup failed.")
                    else:
                        print("Invalid backup selection.")
                        
                elif sub_choice == '3':
                    # Restore
                    print("\n--- Restore Backup ---")
                    print("Supported formats: .enc (Encrypted Zip), .zip (Standard), .vcf (Contacts), .json (SMS)")
                    backup_path = input("Enter path to backup file: ").strip()
                    if os.path.exists(backup_path):
                        print(f"Restoring {backup_path} to device...")
                        bm = BackupManager(selected_device)
                        if bm.restore_backup(backup_path):
                            print("Restore Completed Successfully!")
                        else:
                            print("Restore Failed.")
                    else:
                        print("File not found.")
                
                elif sub_choice == '4':
                    # Developer Options
                    print("\n--- Developer Options ---")
                    print("1. Decrypt Backup File")
                    dev_choice = input("Select option: ").strip()
                    
                    if dev_choice == '1':
                        enc_path = input("Enter path to encrypted file (.enc): ").strip()
                        if os.path.exists(enc_path):
                            bm = BackupManager(selected_device)
                            out = bm.decrypt_backup(enc_path)
                            if out:
                                print(f"File decrypted successfully: {out}")
                            else:
                                print("Decryption failed.")
                        else:
                            print("File not found.")

def main():
    setup_logging()
    
    # If no arguments provided, run interactive mode
    if len(sys.argv) == 1:
        try:
            interactive_mode()
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        return

    # Existing Argument Parser Logic
    parser = argparse.ArgumentParser(description="Android Backup Buddy - IT Diagnostics & Backup Tool")
    
    parser.add_argument("--detect", action="store_true", help="Detect connected devices")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostics on a device")
    parser.add_argument("--backup", action="store_true", help="Perform secure backup")
    
    parser.add_argument("--device-id", type=str, help="Target device ID (required for multiple devices)")
    parser.add_argument("--source", type=str, default="/sdcard/DCIM", help="Source path on device for backup (default: /sdcard/DCIM)")
    parser.add_argument("--dest", type=str, default="backups", help="Local destination folder for backups")
    
    args = parser.parse_args()
    
    # 1. Device Detection
    if args.detect:
        devices = get_connected_devices()
        if not devices:
            print("No devices found.")
        else:
            print("Connected Devices:")
            for d in devices:
                print(f"  - ID: {d['id']} | Status: {d['status']}")
        return

    # Helper: Resolve Device ID
    device_id = args.device_id
    if (args.diagnose or args.backup) and not device_id:
        devices = get_connected_devices()
        if not devices:
            logging.error("No devices found. Connect a device first.")
            return
        if len(devices) == 1:
            device_id = devices[0]['id']
            logging.info(f"Auto-selecting single device: {device_id}")
        else:
            logging.error("Multiple devices found. Please specify --device-id.")
            # Print devices to help user
            for d in devices:
                print(f"  - {d['id']}")
            return

    # 2. Diagnostics
    if args.diagnose:
        logging.info(f"Running diagnostics for {device_id}...")
        diag = Diagnostics(device_id)
        report_path = diag.generate_report()
        if report_path:
            print("-" * 30)
            # Read and print report content for immediate feedback
            with open(report_path, 'r') as f:
                print(f.read())
            print(f"Report saved to: {report_path}")
            print("-" * 30)
    
    # 3. Backup
    if args.backup:
        logging.info(f"Starting backup for {device_id}...")
        bm = BackupManager(device_id)
        encrypted_file = bm.backup_device(args.source, args.dest)
        if encrypted_file:
            print(f"Backup completed successfully: {encrypted_file}")
            print(f"Encryption key saved in current directory as 'backup_key.key'. KEEP THIS SAFE!")
        else:
            logging.error("Backup failed.")

if __name__ == "__main__":
    main()
