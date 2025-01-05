# processor.py

import piexif

def extract_metadata(image_path):
    try:
        exif_data = piexif.load(image_path)
        return exif_data
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return None