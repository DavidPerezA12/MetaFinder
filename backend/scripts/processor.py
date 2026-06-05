import logging
import math
import warnings
from datetime import datetime
from typing import Any, Dict

import piexif
from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_PIXELS = 50_000_000

METADATA_SECTIONS = (
    'basic_info',
    'technical_info',
    'gps_info',
    'advanced_info',
    'other_info',
)

FLASH_STATES = {
    0x0000: 'Did not fire',
    0x0001: 'Fired',
    0x0005: 'Fired, return light not detected',
    0x0007: 'Fired, return light detected',
    0x0008: 'On, did not fire',
    0x0009: 'On, fired',
    0x000D: 'On, return light not detected',
    0x000F: 'On, return light detected',
    0x0010: 'Off, did not fire',
    0x0018: 'Auto, did not fire',
    0x0019: 'Auto, fired',
    0x001D: 'Auto, return light not detected',
    0x001F: 'Auto, return light detected',
}

SCENE_TYPES = {
    0: 'Standard',
    1: 'Landscape',
    2: 'Portrait',
    3: 'Night scene',
}

SHARPNESS = {
    0: 'Normal',
    1: 'Soft',
    2: 'Hard',
}

CONTRAST = {
    0: 'Normal',
    1: 'Soft',
    2: 'Hard',
}

SATURATION = {
    0: 'Normal',
    1: 'Low',
    2: 'High',
}

EXPOSURE_PROGRAMS = {
    0: 'Not defined',
    1: 'Manual',
    2: 'Normal',
    3: 'Aperture priority',
    4: 'Shutter priority',
    5: 'Creative',
    6: 'Action',
    7: 'Portrait',
    8: 'Landscape',
}

METERING_MODES = {
    0: 'Unknown',
    1: 'Average',
    2: 'Center-weighted average',
    3: 'Spot',
    4: 'Multi-spot',
    5: 'Pattern',
    6: 'Partial',
}

ORIENTATION = {
    1: 'Normal',
    2: 'Mirrored horizontally',
    3: 'Rotated 180°',
    4: 'Mirrored vertically',
    5: 'Mirrored horizontally and rotated 270°',
    6: 'Rotated 90°',
    7: 'Mirrored horizontally and rotated 90°',
    8: 'Rotated 270°',
}

HANDLED_EXIF_TAGS = {
    '0th': {
        piexif.ImageIFD.Make,
        piexif.ImageIFD.Model,
        piexif.ImageIFD.Software,
        piexif.ImageIFD.Copyright,
        piexif.ImageIFD.Artist,
        piexif.ImageIFD.Orientation,
        piexif.ImageIFD.XResolution,
        piexif.ImageIFD.YResolution,
        piexif.ImageIFD.ExifTag,
        piexif.ImageIFD.GPSTag,
    },
    'Exif': {
        piexif.ExifIFD.DateTimeOriginal,
        piexif.ExifIFD.ExposureTime,
        piexif.ExifIFD.FNumber,
        piexif.ExifIFD.ISOSpeedRatings,
        piexif.ExifIFD.FocalLength,
        piexif.ExifIFD.LensModel,
        piexif.ExifIFD.ExposureBiasValue,
        piexif.ExifIFD.Flash,
        piexif.ExifIFD.SceneCaptureType,
        piexif.ExifIFD.DigitalZoomRatio,
        piexif.ExifIFD.Sharpness,
        piexif.ExifIFD.Contrast,
        piexif.ExifIFD.Saturation,
        piexif.ExifIFD.ExposureProgram,
        piexif.ExifIFD.MeteringMode,
        piexif.ExifIFD.WhiteBalance,
    },
    'GPS': {
        piexif.GPSIFD.GPSLatitudeRef,
        piexif.GPSIFD.GPSLatitude,
        piexif.GPSIFD.GPSLongitudeRef,
        piexif.GPSIFD.GPSLongitude,
        piexif.GPSIFD.GPSAltitude,
        piexif.GPSIFD.GPSAltitudeRef,
    },
}

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class ImageProcessingError(Exception):
    pass


def _ratio_to_float(value) -> float:
    num, den = value
    if den == 0:
        raise ValueError("EXIF fraction has a zero denominator")
    return num / den


def _safe_decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='ignore').strip('\x00 ')
    return str(value).strip('\x00 ')


def _serialize_metadata_value(value: Any) -> Any:
    if isinstance(value, bytes):
        decoded = _safe_decode(value)
        return decoded if decoded else f"{len(value)} bytes"
    if isinstance(value, tuple):
        return [_serialize_metadata_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_metadata_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_metadata_value(item) for key, item in value.items()}
    return value


def _convert_to_degrees(value):
    d_num, d_den = value[0]
    m_num, m_den = value[1]
    s_num, s_den = value[2]

    degrees = _ratio_to_float((d_num, d_den))
    minutes = _ratio_to_float((m_num, m_den))
    seconds = _ratio_to_float((s_num, s_den))

    return degrees + (minutes / 60.0) + (seconds / 3600.0)


def _format_date(date_str):
    decoded = _safe_decode(date_str)
    try:
        return datetime.strptime(decoded, '%Y:%m:%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
    except ValueError:
        return decoded


def _format_exposure_time(exposure):
    num, den = exposure
    if num == 0 or den == 0:
        return 'N/A'
    if den == 1:
        return f"{num} s"
    return f"1/{den/num:.0f} s"


def _format_fnumber(fnumber):
    num, den = fnumber
    if den == 0:
        return 'N/A'
    return f"f/{num / den:.1f}"


def _set_if_present(source, tag, target, label, formatter=lambda value: value):
    if tag not in source:
        return

    try:
        formatted = formatter(source[tag])
        if formatted is not None:
            target[label] = formatted
    except Exception as e:
        logger.warning(f"Error processing EXIF tag {label}: {str(e)}")


def _format_focal_length(value):
    num, den = value
    return f"{num / den:.0f}mm" if den else 'N/A'


def _format_digital_zoom(value):
    if not isinstance(value, tuple) or len(value) != 2:
        return None

    ratio = _ratio_to_float(value)
    return f"{ratio:.1f}x" if ratio > 1 else "Not used"


def _format_aspect_ratio(width: int, height: int) -> str:
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _format_resolution(value):
    if not isinstance(value, tuple) or len(value) != 2:
        return None

    ratio = _ratio_to_float(value)
    return f"{ratio:.0f} dpi"


def _empty_metadata() -> Dict[str, Dict[str, Any]]:
    return {section: {} for section in METADATA_SECTIONS}


def _load_exif_data(image_path: str) -> Dict[str, Any]:
    try:
        return piexif.load(image_path)
    except Exception as e:
        logger.warning(f"Error extracting EXIF data: {str(e)}")
        return {}


def _add_pillow_metadata(img: Image.Image, metadata: Dict[str, Dict[str, Any]]) -> None:
    metadata['basic_info']['Format'] = img.format
    metadata['basic_info']['Color mode'] = img.mode
    metadata['basic_info']['Dimensions'] = f"{img.width} x {img.height}"
    metadata['technical_info']['Resolution'] = f"{img.width}x{img.height} px"
    metadata['technical_info']['Aspect ratio'] = _format_aspect_ratio(img.width, img.height)
    metadata['technical_info']['Color depth'] = (
        f"{img.bits} bits" if hasattr(img, 'bits') else 'N/A'
    )
    metadata['technical_info']['Channels'] = len(img.getbands())

    if img.info.get('dpi'):
        x_dpi, y_dpi = img.info['dpi']
        metadata['technical_info']['DPI'] = f"{round(x_dpi)} x {round(y_dpi)}"

    if getattr(img, 'is_animated', False):
        metadata['other_info']['Animated'] = 'Yes'
        metadata['other_info']['Frames'] = getattr(img, 'n_frames', 1)

    if 'icc_profile' in img.info:
        metadata['other_info']['ICC profile'] = f"{len(img.info['icc_profile'])} bytes"

    if 'transparency' in img.info or img.mode in ('RGBA', 'LA'):
        metadata['other_info']['Transparency'] = 'Yes'

    ignored_info_keys = {'exif', 'icc_profile', 'dpi', 'transparency'}
    textual_metadata = {}
    for key, value in img.info.items():
        if key in ignored_info_keys:
            continue
        if isinstance(value, (str, int, float, bool)):
            textual_metadata[key] = value
        elif isinstance(value, bytes):
            decoded = _safe_decode(value)
            textual_metadata[key] = decoded if decoded else f"{len(value)} bytes"

    if textual_metadata:
        metadata['other_info']['Format metadata'] = textual_metadata


def _add_basic_exif_metadata(exif_data: Dict[str, Any], metadata: Dict[str, Dict[str, Any]]) -> None:
    basic_info = exif_data.get('0th', {})
    target = metadata['basic_info']
    technical_target = metadata['technical_info']

    _set_if_present(basic_info, piexif.ImageIFD.Make, target, 'Make', _safe_decode)
    _set_if_present(basic_info, piexif.ImageIFD.Model, target, 'Model', _safe_decode)
    _set_if_present(basic_info, piexif.ImageIFD.Software, target, 'Software', _safe_decode)
    _set_if_present(basic_info, piexif.ImageIFD.Copyright, target, 'Copyright', _safe_decode)
    _set_if_present(basic_info, piexif.ImageIFD.Artist, target, 'Artist', _safe_decode)
    _set_if_present(basic_info, piexif.ImageIFD.Orientation, target, 'Orientation', lambda value: ORIENTATION.get(value, 'Unknown'))
    _set_if_present(basic_info, piexif.ImageIFD.XResolution, technical_target, 'Horizontal resolution', _format_resolution)
    _set_if_present(basic_info, piexif.ImageIFD.YResolution, technical_target, 'Vertical resolution', _format_resolution)


def _add_technical_exif_metadata(exif_data: Dict[str, Any], metadata: Dict[str, Dict[str, Any]]) -> None:
    exif_info = exif_data.get('Exif', {})
    target = metadata['technical_info']

    _set_if_present(exif_info, piexif.ExifIFD.DateTimeOriginal, target, 'Capture date', _format_date)
    _set_if_present(exif_info, piexif.ExifIFD.ExposureTime, target, 'Exposure time', _format_exposure_time)
    _set_if_present(exif_info, piexif.ExifIFD.FNumber, target, 'Aperture', _format_fnumber)
    _set_if_present(exif_info, piexif.ExifIFD.ISOSpeedRatings, target, 'ISO', str)
    _set_if_present(exif_info, piexif.ExifIFD.FocalLength, target, 'Focal length', _format_focal_length)
    _set_if_present(exif_info, piexif.ExifIFD.LensModel, target, 'Lens model', _safe_decode)
    _set_if_present(exif_info, piexif.ExifIFD.ExposureBiasValue, target, 'Exposure compensation', lambda value: f"{_ratio_to_float(value):.1f} EV")


def _add_advanced_exif_metadata(exif_data: Dict[str, Any], metadata: Dict[str, Dict[str, Any]]) -> None:
    exif_info = exif_data.get('Exif', {})
    target = metadata['advanced_info']

    _set_if_present(exif_info, piexif.ExifIFD.Flash, target, 'Flash', lambda value: FLASH_STATES.get(value, 'Unknown'))
    _set_if_present(exif_info, piexif.ExifIFD.SceneCaptureType, target, 'Scene type', lambda value: SCENE_TYPES.get(value, 'Unknown'))
    _set_if_present(exif_info, piexif.ExifIFD.DigitalZoomRatio, target, 'Digital zoom', _format_digital_zoom)
    _set_if_present(exif_info, piexif.ExifIFD.Sharpness, target, 'Sharpness', lambda value: SHARPNESS.get(value, 'Unknown'))
    _set_if_present(exif_info, piexif.ExifIFD.Contrast, target, 'Contrast', lambda value: CONTRAST.get(value, 'Unknown'))
    _set_if_present(exif_info, piexif.ExifIFD.Saturation, target, 'Saturation', lambda value: SATURATION.get(value, 'Unknown'))
    _set_if_present(exif_info, piexif.ExifIFD.ExposureProgram, target, 'Exposure program', lambda value: EXPOSURE_PROGRAMS.get(value, 'Unknown'))
    _set_if_present(exif_info, piexif.ExifIFD.MeteringMode, target, 'Metering mode', lambda value: METERING_MODES.get(value, 'Other'))
    _set_if_present(exif_info, piexif.ExifIFD.WhiteBalance, target, 'White balance', lambda value: 'Manual' if value == 1 else 'Auto')


def _add_gps_coordinates(gps_data: Dict[str, Any], target: Dict[str, Any]) -> None:
    if piexif.GPSIFD.GPSLatitude not in gps_data or piexif.GPSIFD.GPSLongitude not in gps_data:
        return

    lat_ref = _safe_decode(gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N'))
    lon_ref = _safe_decode(gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E'))

    lat_degs = _convert_to_degrees(gps_data[piexif.GPSIFD.GPSLatitude])
    lon_degs = _convert_to_degrees(gps_data[piexif.GPSIFD.GPSLongitude])

    if lat_ref.upper() == 'S':
        lat_degs = -lat_degs
    if lon_ref.upper() == 'W':
        lon_degs = -lon_degs

    target['Latitude'] = f"{abs(lat_degs):.6f}° {'S' if lat_degs < 0 else 'N'}"
    target['Longitude'] = f"{abs(lon_degs):.6f}° {'W' if lon_degs < 0 else 'E'}"
    target['Decimal coordinates'] = {
        'latitude': lat_degs,
        'longitude': lon_degs,
    }


def _add_gps_altitude(gps_data: Dict[str, Any], target: Dict[str, Any]) -> None:
    if piexif.GPSIFD.GPSAltitude not in gps_data:
        return

    altitude = _ratio_to_float(gps_data[piexif.GPSIFD.GPSAltitude])
    ref = gps_data.get(piexif.GPSIFD.GPSAltitudeRef, 0)
    altitude = -altitude if ref in (1, b'\x01', b'1', '1') else altitude
    target['Altitude'] = f"{altitude:.1f} meters"


def _add_gps_metadata(exif_data: Dict[str, Any], metadata: Dict[str, Dict[str, Any]]) -> None:
    gps_data = exif_data.get('GPS', {})
    if not gps_data:
        return

    target = metadata['gps_info']
    try:
        _add_gps_coordinates(gps_data, target)
    except Exception as e:
        logger.warning(f"Error processing GPS coordinates: {str(e)}")

    try:
        _add_gps_altitude(gps_data, target)
    except Exception as e:
        logger.warning(f"Error processing GPS altitude: {str(e)}")


def _add_exif_metadata(exif_data: Dict[str, Any], metadata: Dict[str, Dict[str, Any]]) -> None:
    _add_basic_exif_metadata(exif_data, metadata)
    _add_technical_exif_metadata(exif_data, metadata)
    _add_advanced_exif_metadata(exif_data, metadata)
    _add_gps_metadata(exif_data, metadata)
    _add_unmapped_exif_metadata(exif_data, metadata)


def _get_tag_name(ifd_name: str, tag: int) -> str:
    tag_info = piexif.TAGS.get(ifd_name, {}).get(tag, {})
    return tag_info.get('name') or f"Tag {tag}"


def _add_unmapped_exif_metadata(exif_data: Dict[str, Any], metadata: Dict[str, Dict[str, Any]]) -> None:
    unmapped = {}

    for ifd_name in ('0th', 'Exif', 'GPS', 'Interop', '1st'):
        ifd_data = exif_data.get(ifd_name, {})
        if not isinstance(ifd_data, dict):
            continue

        handled_tags = HANDLED_EXIF_TAGS.get(ifd_name, set())
        remaining_tags = {}
        for tag, value in ifd_data.items():
            if tag in handled_tags:
                continue
            remaining_tags[_get_tag_name(ifd_name, tag)] = _serialize_metadata_value(value)

        if remaining_tags:
            unmapped[ifd_name] = remaining_tags

    thumbnail = exif_data.get('thumbnail')
    if thumbnail:
        unmapped['thumbnail'] = f"{len(thumbnail)} bytes"

    if unmapped:
        metadata['other_info']['Unmapped EXIF'] = unmapped


def extract_metadata(image_path: str) -> Dict[str, Any]:
    metadata = _empty_metadata()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(image_path) as img:
                _add_pillow_metadata(img, metadata)
                if img.format in ['JPEG', 'TIFF']:
                    _add_exif_metadata(_load_exif_data(image_path), metadata)

        return metadata

    except Exception as e:
        raise ImageProcessingError(f"Error processing image: {str(e)}")
