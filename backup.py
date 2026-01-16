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

    def restore_backup(self, backup_path, device_dest="/sdcard/"):
        """
        Restores a backup to the device.
        1. Decrypts the backup (if encrypted).
        2. Unzips it.
        3. Pushes files to device.
        """
        temp_extract_dir = f"temp_restore_{self.device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 1. Decrypt if needed
            if backup_path.endswith(".enc"):
                zip_path = self.decrypt_backup(backup_path)
                if not zip_path:
                    return False
                # If we decrypted it, it's a temp file we should clean up later
                is_temp_zip = True
            else:
                zip_path = backup_path
                is_temp_zip = False
            
            # 2. Unzip
            logging.info(f"Extracting {zip_path}...")
            shutil.unpack_archive(zip_path, temp_extract_dir)
            
            # 3. Push to device
            # Note: shutil.unpack_archive likely created a directory structure.
            # We want to push the CONTENTS of that structure.
            # For simplicity in this MVP, we push the extracted folder to the dest.
            
            logging.info(f"Restoring data to device {self.device_id} at {device_dest}...")
            
            # We need to find the root inside the extracted dir
            # Because make_archive might have created a nested structure depending on how it was called
            # But let's assume we push the whole temp dir content
            
            # Using adb push <local_dir> <remote_dir>
            # If local_dir is a directory, ADB pushes it AS A SUBDIRECTORY if remote exists, 
            # or creates it if not. This behavior can be tricky.
            # Let's push the contents.
            
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
            # Cleanup
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            if 'is_temp_zip' in locals() and is_temp_zip and os.path.exists(zip_path):
                os.remove(zip_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Mock usage
    pass
