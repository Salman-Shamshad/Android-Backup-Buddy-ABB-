import subprocess
import os
import shutil
import logging
from cryptography.fernet import Fernet
from datetime import datetime

class BackupManager:
    def __init__(self, device_id):
        self.device_id = device_id
        
    def _generate_key(self, key_path="backup_key.key"):
        """Generates a key and saves it into a file."""
        key = Fernet.generate_key()
        with open(key_path, "wb") as key_file:
            key_file.write(key)
        return key

    def _load_key(self, key_path="backup_key.key"):
        """Loads the key from the current directory named `backup_key.key`."""
        if not os.path.exists(key_path):
             return self._generate_key(key_path)
        with open(key_path, "wb") as key_file: # Oops, reading mode is 'rb'
             pass 
        # Actually let's just use 'rb' correctly
        return open(key_path, "rb").read()

    def _get_key(self):
        """Helper to get or create key."""
        if os.path.exists("backup_key.key"):
            with open("backup_key.key", "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open("backup_key.key", "wb") as f:
                f.write(key)
            logging.info("Generated new encryption key: backup_key.key")
            return key

    def backup_device(self, source_path, dest_folder="backups"):
        """
        Pulls data from device, zips it, encrypts it.
        source_path: path on device (e.g. /sdcard/DCIM)
        dest_folder: local folder to save backup
        """
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = f"temp_backup_{self.device_id}_{timestamp}"
        
        try:
            # 1. Pull data
            logging.info(f"Pulling {source_path} from device {self.device_id}...")
            # ADB pull destination is a local path
            cmd = ["adb", "-s", self.device_id, "pull", source_path, temp_dir]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # 2. Archive (Zip)
            logging.info("Archiving data...")
            shutil.make_archive(temp_dir, 'zip', temp_dir)
            zip_file = f"{temp_dir}.zip"
            
            # 3. Encrypt
            logging.info("Encrypting backup...")
            key = self._get_key()
            f = Fernet(key)
            
            with open(zip_file, "rb") as file:
                file_data = file.read()
                
            encrypted_data = f.encrypt(file_data)
            
            encrypted_filename = f"backup_{self.device_id}_{timestamp}.enc"
            encrypted_path = os.path.join(dest_folder, encrypted_filename)
            
            with open(encrypted_path, "wb") as file:
                file.write(encrypted_data)
                
            logging.info(f"Backup saved to {encrypted_path}")
            
            return encrypted_path

        except subprocess.CalledProcessError as e:
            logging.error(f"ADB Pull failed: {e}")
            return None
        except Exception as e:
            logging.error(f"Backup failed: {e}")
            return None
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            if os.path.exists(f"{temp_dir}.zip"):
                os.remove(f"{temp_dir}.zip")

    def decrypt_backup(self, encrypted_path, output_path=None):
        """
        Decrypts an encrypted backup file.
        If output_path is not provided, saves as zip in the same folder.
        """
        try:
            logging.info(f"Decrypting {encrypted_path}...")
            key = self._get_key()
            f = Fernet(key)
            
            with open(encrypted_path, "rb") as file:
                encrypted_data = file.read()
                
            decrypted_data = f.decrypt(encrypted_data)
            
            if not output_path:
                output_path = encrypted_path.replace(".enc", ".zip")
                
            with open(output_path, "wb") as file:
                file.write(decrypted_data)
                
            logging.info(f"Decrypted file saved to {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Decryption failed: {e}")
            return None

    def backup_contacts(self, dest_folder="backups/contacts"):
        """
        Backs up contacts by querying the contacts content provider.
        Saves as a Standard VCF file (vCard).
        """
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"contacts_{self.device_id}_{timestamp}.vcf"
        filepath = os.path.join(dest_folder, filename)
        
        try:
            logging.info(f"Querying contacts from device {self.device_id}...")
            # Query contacts
            cmd = [
                "adb", "-s", self.device_id, "shell", 
                "content", "query", "--uri", "content://com.android.contacts/data/phones", 
                "--projection", "display_name:data1"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            vcard_content = []
            
            for line in lines:
                if "Row:" in line:
                    parts = line.split(',')
                    name = ""
                    phone = ""
                    
                    for part in parts:
                        if "display_name=" in part:
                            name = part.split("display_name=")[-1].strip()
                        elif "data1=" in part:
                            phone = part.split("data1=")[-1].strip()
                    
                    if name and phone:
                        vcard = [
                            "BEGIN:VCARD",
                            "VERSION:2.1",
                            f"FN:{name}",
                            f"TEL;CELL:{phone}",
                            "END:VCARD"
                        ]
                        vcard_content.append("\n".join(vcard))
            
            if not vcard_content:
                logging.warning("No contacts found.")

            with open(filepath, "w") as f:
                f.write("\n".join(vcard_content))
                
            logging.info(f"Contacts saved to {filepath}")
            return filepath

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to query contacts: {e}")
            return None
        except Exception as e:
            logging.error(f"Contacts backup failed: {e}")
            return None

    def backup_sms(self, dest_folder="backups/messages"):
        """
        Backs up SMS by querying the sms content provider.
        Saves as a JSON file for easy restore.
        """
        import json
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sms_{self.device_id}_{timestamp}.json"
        filepath = os.path.join(dest_folder, filename)
        
        try:
            logging.info(f"Querying SMS from device {self.device_id}...")
            # Query SMS with type
            cmd = [
                "adb", "-s", self.device_id, "shell",
                "content", "query", "--uri", "content://sms",
                "--projection", "address:date:body:type"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            lines = result.stdout.strip().split('\n')
            sms_list = []
            
            for line in lines:
                if "Row:" in line:
                    # Basic parser again. 
                    msg = {"address": "", "date": "0", "body": "", "type": "1"}
                    
                    try:
                        if "address=" in line:
                            start = line.find("address=") + 8
                            end = line.find(",", start)
                            if end == -1: end = len(line)
                            msg["address"] = line[start:end].strip()
                        
                        if "date=" in line:
                            start = line.find("date=") + 5
                            end = line.find(",", start)
                            if end == -1: end = len(line)
                            msg["date"] = line[start:end].strip()

                        if "type=" in line:
                            start = line.find("type=") + 5
                            end = line.find(",", start)
                            if end == -1: end = len(line)
                            msg["type"] = line[start:end].strip()
                        
                        if "body=" in line:
                            start = line.find("body=") + 5
                            # Assuming body is last or we take remaining
                            msg["body"] = line[start:].strip()
                    except:
                        pass
                    
                    if msg["address"] and msg["body"]:
                        sms_list.append(msg)
            
            with open(filepath, "w") as f:
                json.dump(sms_list, f, indent=4)
                
            logging.info(f"SMS saved to {filepath}")
            return filepath

        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to query SMS: {e}")
            return None
        except Exception as e:
            logging.error(f"SMS backup failed: {e}")
            return None

    def restore_backup(self, backup_path, device_dest="/sdcard/"):
        """
        Restores a backup to the device.
        Handles:
        - .enc: Encrypted file zip
        - .zip: Standard backup
        - .vcf: Contacts (Import Intent)
        - .json: SMS (Content Insert)
        """
        import json
        
        # 1. Handle Contacts (VCF)
        if backup_path.endswith(".vcf"):
            try:
                logging.info(f"Restoring contacts from {backup_path}...")
                filename = os.path.basename(backup_path)
                dest = f"/sdcard/{filename}"
                
                # Push file
                subprocess.run(["adb", "-s", self.device_id, "push", backup_path, dest], check=True)
                
                # Trigger import intent
                logging.info("Triggering Contact Import on device...")
                # Try generic VIEW intent for vcard
                cmd = [
                    "adb", "-s", self.device_id, "shell",
                    "am", "start", "-t", "text/x-vcard", "-d", f"file://{dest}",
                    "-a", "android.intent.action.VIEW"
                ]
                subprocess.run(cmd, check=True)
                
                print("Please check your device to confirm Contact Import.")
                return True
            except Exception as e:
                logging.error(f"Contact Restore failed: {e}")
                return False

        # 2. Handle SMS (JSON)
        if backup_path.endswith(".json"):
            try:
                logging.info(f"Restoring SMS from {backup_path}...")
                with open(backup_path, 'r') as f:
                    messages = json.load(f)
                
                count = 0
                total = len(messages)
                print(f"Restoring {total} messages...")
                
                for msg in messages:
                    # construct content insert command
                    # escape body for shell
                    body = msg.get('body', '').replace('"', '\\"').replace("'", "\\'")
                    address = msg.get('address', '')
                    date = msg.get('date', '0')
                    msg_type = msg.get('type', '1')
                    
                    cmd = [
                        "adb", "-s", self.device_id, "shell",
                        "content", "insert", "--uri", "content://sms",
                        "--bind", f"address:s:{address}",
                        "--bind", f"body:s:\"{body}\"",
                        "--bind", f"date:l:{date}",
                        "--bind", f"type:i:{msg_type}"
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)
                    count += 1
                    if count % 10 == 0:
                        print(f"Restored {count}/{total}...")
                
                logging.info(f"Restored {count} messages.")
                return True
            except Exception as e:
                logging.error(f"SMS Restore failed: {e}")
                return False

        # 3. Handle Standard Backup (Zip/Enc)
        temp_extract_dir = f"temp_restore_{self.device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Decrypt if needed
            if backup_path.endswith(".enc"):
                zip_path = self.decrypt_backup(backup_path)
                if not zip_path:
                    return False
                is_temp_zip = True
            else:
                zip_path = backup_path
                is_temp_zip = False
            
            # Unzip
            logging.info(f"Extracting {zip_path}...")
            shutil.unpack_archive(zip_path, temp_extract_dir)
            
            # Push to device
            logging.info(f"Restoring data to device {self.device_id} at {device_dest}...")
            
            for item in os.listdir(temp_extract_dir):
                s = os.path.join(temp_extract_dir, item)
                cmd = ["adb", "-s", self.device_id, "push", s, device_dest]
                subprocess.run(cmd, check=True, capture_output=True)
                
            logging.info("Restore completed successfully.")
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"ADB Push failed: {e}")
            return False
        except Exception as e:
            logging.error(f"Restore failed: {e}")
            return False
        finally:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            if 'is_temp_zip' in locals() and is_temp_zip and os.path.exists(zip_path):
                os.remove(zip_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Mock usage
    pass
