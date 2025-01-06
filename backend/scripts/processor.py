import piexif
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

def extract_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extrae los metadatos EXIF de una imagen usando piexif.
    
    Args:
        image_path: Ruta al archivo de imagen
        
    Returns:
        Dict[str, Any]: Metadatos de la imagen en categorías
    """
    try:
        exif_data = piexif.load(image_path)
        
        metadata = {
            'información_básica': {},
            'información_técnica': {},
            'información_gps': {},
            'otros': {}
        }
        
        # Asignamos algunas etiquetas de ImageIFD
        for tag, value in exif_data.get('0th', {}).items():
            tag_name = piexif.TAGS["0th"].get(tag, {}).get('name', f'Tag_{tag}')
            metadata['información_básica'][tag_name] = str(value)

        # EXIF data
        for tag, value in exif_data.get('Exif', {}).items():
            tag_name = piexif.TAGS["Exif"].get(tag, {}).get('name', f'Tag_{tag}')
            metadata['información_técnica'][tag_name] = str(value)
        
        # GPS data
        gps_data = exif_data.get('GPS', {})
        if gps_data:
            for tag, value in gps_data.items():
                tag_name = piexif.TAGS["GPS"].get(tag, {}).get('name', f'Tag_{tag}')
                metadata['información_gps'][tag_name] = str(value)
            
            # Si contiene lat y long, intentamos convertir a decimal
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
                
                metadata['información_gps']['GPSDecimalLatitude'] = lat_degs
                metadata['información_gps']['GPSDecimalLongitude'] = lon_degs
        
        # Teóricamente, podemos incluir '1st' (miniaturas) y 'Interop' si fuera necesario
        # Los metadatos que no entren en las categorías anteriores, los consideramos "otros"
        # Sin embargo, 'piexif' ya nos separa la info en diccionarios: '0th', 'Exif', 'GPS', '1st', 'Interop'
        # Si quisieras unificar más datos, podrías procesarlos aquí.

        return metadata

    except Exception as e:
        raise ImageProcessingError(f"Error al procesar la imagen: {str(e)}")
