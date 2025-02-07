import piexif
from PIL import Image
from datetime import datetime
from typing import Any, Dict

class ImageProcessingError(Exception):
    """Excepción personalizada para errores de procesamiento de imágenes."""
    pass

def _convert_to_degrees(value):
    """
    Convierte el valor de GPS (en formato de fracciones) a formato decimal.
    
    Args:
        value (tuple): Tupla con fracciones (numerador, denominador)
    
    Returns:
        float: Valor en grados decimales
    """
    d_num, d_den = value[0]
    m_num, m_den = value[1]
    s_num, s_den = value[2]

    degrees = d_num / d_den
    minutes = m_num / m_den
    seconds = s_num / s_den

    return degrees + (minutes / 60.0) + (seconds / 3600.0)

def _format_date(date_str):
    """Formatea la fecha EXIF a un formato más legible."""
    try:
        return datetime.strptime(date_str.decode('utf-8', errors='ignore'), '%Y:%m:%d %H:%M:%S').strftime('%d/%m/%Y %H:%M:%S')
    except:
        return date_str.decode('utf-8', errors='ignore')

def _format_exposure_time(exposure):
    """Formatea el tiempo de exposición a una fracción legible."""
    num, den = exposure
    if den == 1:
        return f"{num} s"
    return f"1/{den/num:.0f} s"

def _format_fnumber(fnumber):
    """Formatea el número F a un formato estándar."""
    num, den = fnumber
    return f"f/{num/den:.1f}"

def extract_metadata(image_path: str) -> Dict[str, Any]:
    """Extrae y formatea los metadatos de una imagen."""
    metadata = {
        'información_básica': {},
        'información_técnica': {},
        'información_gps': {},
        'información_avanzada': {},
        'otros': {}
    }

    try:
        # Primero obtenemos información básica usando PIL
        with Image.open(image_path) as img:
            metadata['información_básica']['Formato'] = img.format
            metadata['información_básica']['Modo'] = img.mode
            metadata['información_técnica']['Resolución'] = f"{img.width}x{img.height} px"
            metadata['información_técnica']['Profundidad de color'] = f"{img.bits} bits" if hasattr(img, 'bits') else 'N/A'

            # Intentamos extraer EXIF solo si el formato lo soporta
            if img.format in ['JPEG', 'TIFF']:
                try:
                    exif_data = piexif.load(image_path)
                    
                    # Información básica mejorada
                    basic_info = exif_data.get('0th', {})
                    if basic_info:
                        if piexif.ImageIFD.Make in basic_info:
                            metadata['información_básica']['Fabricante'] = basic_info[piexif.ImageIFD.Make].decode('utf-8', errors='ignore')
                        if piexif.ImageIFD.Model in basic_info:
                            metadata['información_básica']['Modelo'] = basic_info[piexif.ImageIFD.Model].decode('utf-8', errors='ignore')
                        if piexif.ImageIFD.Software in basic_info:
                            metadata['información_básica']['Software'] = basic_info[piexif.ImageIFD.Software].decode('utf-8', errors='ignore')
                        if piexif.ImageIFD.Copyright in basic_info:
                            metadata['información_básica']['Copyright'] = basic_info[piexif.ImageIFD.Copyright].decode('utf-8', errors='ignore')
                        if piexif.ImageIFD.Artist in basic_info:
                            metadata['información_básica']['Artista'] = basic_info[piexif.ImageIFD.Artist].decode('utf-8', errors='ignore')

                    # Información técnica mejorada
                    exif_info = exif_data.get('Exif', {})
                    if exif_info:
                        if piexif.ExifIFD.DateTimeOriginal in exif_info:
                            metadata['información_técnica']['Fecha de captura'] = _format_date(exif_info[piexif.ExifIFD.DateTimeOriginal])
                        if piexif.ExifIFD.ExposureTime in exif_info:
                            metadata['información_técnica']['Tiempo de exposición'] = _format_exposure_time(exif_info[piexif.ExifIFD.ExposureTime])
                        if piexif.ExifIFD.FNumber in exif_info:
                            metadata['información_técnica']['Apertura'] = _format_fnumber(exif_info[piexif.ExifIFD.FNumber])
                        if piexif.ExifIFD.ISOSpeedRatings in exif_info:
                            metadata['información_técnica']['ISO'] = str(exif_info[piexif.ExifIFD.ISOSpeedRatings])
                        if piexif.ExifIFD.FocalLength in exif_info:
                            num, den = exif_info[piexif.ExifIFD.FocalLength]
                            metadata['información_técnica']['Distancia focal'] = f"{num/den:.0f}mm"
                        if piexif.ExifIFD.LensModel in exif_info:
                            metadata['información_técnica']['Modelo de lente'] = exif_info[piexif.ExifIFD.LensModel].decode('utf-8', errors='ignore')

                        # Información avanzada ampliada
                        if piexif.ExifIFD.Flash in exif_info:
                            flash_info = exif_info[piexif.ExifIFD.Flash]
                            flash_states = {
                                0x0000: 'No disparó',
                                0x0001: 'Disparó',
                                0x0005: 'Disparó, no se detectó retorno de luz',
                                0x0007: 'Disparó, se detectó retorno de luz',
                                0x0008: 'On, no disparó',
                                0x0009: 'On, disparó',
                                0x000D: 'On, no se detectó retorno de luz',
                                0x000F: 'On, se detectó retorno de luz',
                                0x0010: 'Off, no disparó',
                                0x0018: 'Auto, no disparó',
                                0x0019: 'Auto, disparó',
                                0x001D: 'Auto, no se detectó retorno de luz',
                                0x001F: 'Auto, se detectó retorno de luz'
                            }
                            metadata['información_avanzada']['Flash'] = flash_states.get(flash_info, 'Desconocido')
                        
                        if piexif.ExifIFD.SceneCaptureType in exif_info:
                            scene_types = {
                                0: 'Estándar',
                                1: 'Paisaje',
                                2: 'Retrato',
                                3: 'Escena nocturna'
                            }
                            metadata['información_avanzada']['Tipo de escena'] = scene_types.get(exif_info[piexif.ExifIFD.SceneCaptureType], 'Desconocido')
                        
                        if piexif.ExifIFD.DigitalZoomRatio in exif_info:
                            zoom_ratio = exif_info[piexif.ExifIFD.DigitalZoomRatio]
                            if isinstance(zoom_ratio, tuple) and len(zoom_ratio) == 2:
                                ratio = zoom_ratio[0] / zoom_ratio[1]
                                metadata['información_avanzada']['Zoom digital'] = f"{ratio:.1f}x" if ratio > 1 else "No usado"

                        if piexif.ExifIFD.Sharpness in exif_info:
                            sharpness = {
                                0: 'Normal',
                                1: 'Suave',
                                2: 'Fuerte'
                            }
                            metadata['información_avanzada']['Nitidez'] = sharpness.get(exif_info[piexif.ExifIFD.Sharpness], 'Desconocido')

                        if piexif.ExifIFD.Contrast in exif_info:
                            contrast = {
                                0: 'Normal',
                                1: 'Suave',
                                2: 'Fuerte'
                            }
                            metadata['información_avanzada']['Contraste'] = contrast.get(exif_info[piexif.ExifIFD.Contrast], 'Desconocido')

                        if piexif.ExifIFD.Saturation in exif_info:
                            saturation = {
                                0: 'Normal',
                                1: 'Baja',
                                2: 'Alta'
                            }
                            metadata['información_avanzada']['Saturación'] = saturation.get(exif_info[piexif.ExifIFD.Saturation], 'Desconocido')

                        if piexif.ExifIFD.ExposureProgram in exif_info:
                            programs = {
                                0: 'No definido',
                                1: 'Manual',
                                2: 'Normal',
                                3: 'Prioridad de apertura',
                                4: 'Prioridad de obturador',
                                5: 'Creativo',
                                6: 'Acción',
                                7: 'Retrato',
                                8: 'Paisaje'
                            }
                            metadata['información_avanzada']['Programa de exposición'] = programs.get(exif_info[piexif.ExifIFD.ExposureProgram], 'Desconocido')
                        if piexif.ExifIFD.MeteringMode in exif_info:
                            modes = {
                                0: 'Desconocido',
                                1: 'Promedio',
                                2: 'Promedio ponderado al centro',
                                3: 'Puntual',
                                4: 'Multipunto',
                                5: 'Patrón',
                                6: 'Parcial'
                            }
                            metadata['información_avanzada']['Modo de medición'] = modes.get(exif_info[piexif.ExifIFD.MeteringMode], 'Otro')
                        if piexif.ExifIFD.WhiteBalance in exif_info:
                            metadata['información_avanzada']['Balance de blancos'] = 'Manual' if exif_info[piexif.ExifIFD.WhiteBalance] == 1 else 'Automático'

                    # GPS data mejorado
                    gps_data = exif_data.get('GPS', {})
                    if gps_data:
                        if piexif.GPSIFD.GPSLatitude in gps_data and piexif.GPSIFD.GPSLongitude in gps_data:
                            lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode('utf-8', errors='ignore')
                            lon_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode('utf-8', errors='ignore')
                            
                            lat_tuple = gps_data[piexif.GPSIFD.GPSLatitude]
                            lon_tuple = gps_data[piexif.GPSIFD.GPSLongitude]
                            
                            lat_degs = _convert_to_degrees(lat_tuple)
                            lon_degs = _convert_to_degrees(lon_tuple)
                            
                            if lat_ref.upper() == 'S':
                                lat_degs = -lat_degs
                            if lon_ref.upper() == 'W':
                                lon_degs = -lon_degs
                            
                            metadata['información_gps']['Latitud'] = f"{abs(lat_degs):.6f}° {'S' if lat_degs < 0 else 'N'}"
                            metadata['información_gps']['Longitud'] = f"{abs(lon_degs):.6f}° {'W' if lon_degs < 0 else 'E'}"
                            metadata['información_gps']['Coordenadas decimales'] = {
                                'latitud': lat_degs,
                                'longitud': lon_degs
                            }
                        
                        if piexif.GPSIFD.GPSAltitude in gps_data:
                            alt_tuple = gps_data[piexif.GPSIFD.GPSAltitude]
                            altitude = alt_tuple[0] / alt_tuple[1]
                            ref = gps_data.get(piexif.GPSIFD.GPSAltitudeRef, b'0').decode('utf-8', errors='ignore')
                            altitude = -altitude if ref == '1' else altitude
                            metadata['información_gps']['Altitud'] = f"{altitude:.1f} metros"

                except Exception as e:
                    # Si falla la extracción de EXIF, continuamos con los metadatos básicos
                    logger.warning(f"Error al extraer datos EXIF: {str(e)}")

        return metadata

    except Exception as e:
        raise ImageProcessingError(f"Error al procesar la imagen: {str(e)}")
