import subprocess
import logging
import os
from datetime import datetime

class Diagnostics:
    def __init__(self, device_id):
        self.device_id = device_id

    def _run_shell_command(self, command):
        """Runs an ADB shell command on the specific device."""
        full_command = ["adb", "-s", self.device_id, "shell"] + command.split()
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running command '{command}' on device {self.device_id}: {e}")
            return None

    def get_device_info(self):
        """Retrieves model and Android version."""
        model = self._run_shell_command("getprop ro.product.model")
        version = self._run_shell_command("getprop ro.build.version.release")
        return {"model": model, "version": version}

    def get_battery_status(self):
        """Retrieves battery level and status."""
        # Simple parsing of dumpsys battery
        output = self._run_shell_command("dumpsys battery")
        if not output:
            return {}
        
        info = {}
        for line in output.split('\n'):
            line = line.strip()
            if "level" in line:
                info['level'] = line.split(':')[-1].strip()
            elif "status" in line:
                 # Status codes: 1: Unknown, 2: Charging, 3: Discharging, 4: Not charging, 5: Full
                status_code = line.split(':')[-1].strip()
                status_map = {
                    '1': 'Unknown', '2': 'Charging', '3': 'Discharging', 
                    '4': 'Not Charging', '5': 'Full'
                }
                info['status'] = status_map.get(status_code, status_code)
        return info

    def get_storage_info(self):
        """Retrieves storage info for /data partition."""
        # focused on internal storage /data
        output = self._run_shell_command("df /data")
        if not output:
            return {}
        
        lines = output.split('\n')
        if len(lines) > 1:
            # Filesystem 1K-blocks Used Available Use% Mounted on
            # /dev/block/dm-0 ... ... ... ... /data
            parts = lines[1].split()
            if len(parts) >= 6:
                return {
                    "total": parts[1], # In 1K blocks usually
                    "used": parts[2],
                    "available": parts[3],
                    "percent": parts[4]
                }
        return {}

    def generate_report(self, output_dir="reports"):
        """Generates a text report with diagnostics info."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        info = self.get_device_info()
        battery = self.get_battery_status()
        storage = self.get_storage_info()
        
        report_content = [
            f"Diagnostics Report for Device: {self.device_id}",
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "-" * 40,
            f"Model: {info.get('model', 'Unknown')}",
            f"Android Version: {info.get('version', 'Unknown')}",
            "-" * 40,
            "Battery:",
            f"  Level: {battery.get('level', 'Unknown')}%",
            f"  Status: {battery.get('status', 'Unknown')}",
            "-" * 40,
            "Storage (/data):",
            f"  Used: {storage.get('used', 'Unknown')} (1K-blocks)",
            f"  Available: {storage.get('available', 'Unknown')} (1K-blocks)",
            f"  Use%: {storage.get('percent', 'Unknown')}",
            "-" * 40
        ]
        
        filename = f"diagnostics_{self.device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, "w") as f:
                f.write("\n".join(report_content))
            logging.info(f"Report saved to {filepath}")
            return filepath
        except IOError as e:
            logging.error(f"Failed to write report: {e}")
            return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Mock usage: python diagnostics.py
    # This won't really work without a device ID, usually passed from main
    pass
