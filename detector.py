import subprocess
import logging

def get_connected_devices():
    """
    Detects connected devices via ADB.
    Returns a list of dictionaries with 'id' and 'status' keys.
    """
    devices = []
    try:
        # Run adb devices command
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse output
        lines = result.stdout.strip().split('\n')
        # Skip the first line ("List of devices attached")
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                status = parts[1]
                devices.append({'id': device_id, 'status': status})
                
    except FileNotFoundError:
        logging.error("ADB not found. Please ensure ADB is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running ADB: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during device detection: {e}")
        
    return devices

if __name__ == "__main__":
    # Test execution
    logging.basicConfig(level=logging.INFO)
    detected = get_connected_devices()
    print(f"Connected devices: {detected}")
