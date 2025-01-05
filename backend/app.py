from flask import Flask, request, jsonify, send_from_directory, abort
from PIL import Image, ExifTags
from werkzeug.utils import secure_filename
import piexif
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../frontend', static_url_path='/static')
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    """Ruta principal que sirve el frontend."""
    return send_from_directory('../frontend/html', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """
    Procesa la subida de imágenes y extrae sus metadatos.
    
    Returns:
        JSON con los metadatos o mensaje de error
    """
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No se proporcionó ninguna imagen'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de archivo no permitido'}), 400
            
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Verificar que el directorio de subida exista
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        # Guardar archivo temporalmente
        file.save(filepath)
        logger.debug(f"Archivo guardado en: {filepath}")
        
        try:
            metadata = extract_metadata(filepath)
            return jsonify(metadata)
        finally:
            # Limpiar archivo temporal
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Archivo temporal eliminado: {filepath}")
    
    except Exception as e:
        logger.error(f"Error en upload_image: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

def extract_metadata(image_path):
    """
    Extrae los metadatos EXIF de una imagen.
    
    Args:
        image_path: Ruta al archivo de imagen
        
    Returns:
        dict: Metadatos de la imagen
    """
    logger.debug(f"Intentando extraer metadatos de: {image_path}")
    
    try:
        with Image.open(image_path) as image:
            logger.debug(f"Formato de imagen: {image.format}")
            logger.debug(f"Modo de imagen: {image.mode}")
            
            metadata = {}
            
            # Intentar primero con piexif
            try:
                exif_dict = piexif.load(image_path)
                if exif_dict:
                    logger.debug("Datos EXIF encontrados con piexif")
                    for ifd in exif_dict:
                        if ifd == "thumbnail":
                            continue
                        if isinstance(exif_dict[ifd], dict):
                            for tag_id, value in exif_dict[ifd].items():
                                try:
                                    tag_name = piexif.TAGS[ifd][tag_id]["name"]
                                    if isinstance(value, bytes):
                                        try:
                                            value = value.decode('utf-8', 'ignore')
                                        except:
                                            value = value.hex()
                                    elif isinstance(value, tuple) and len(value) == 2:
                                        if value[1] != 0:
                                            value = value[0] / value[1]
                                    metadata[tag_name] = value
                                except KeyError:
                                    metadata[f"Unknown_{ifd}_{tag_id}"] = str(value)
                    
                    if metadata:
                        logger.debug("Metadatos extraídos con éxito usando piexif")
                        return format_metadata(metadata)
            
            except Exception as e:
                logger.debug(f"Error con piexif: {str(e)}")
            
            # Intentar con PIL como respaldo
            logger.debug("Intentando con PIL...")
            exif_data = image._getexif()
            if exif_data is not None:
                logger.debug("Datos EXIF encontrados con PIL")
                for tag, value in exif_data.items():
                    tag_name = ExifTags.TAGS.get(tag, tag)
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', 'ignore')
                        except:
                            value = value.hex()
                    elif isinstance(value, (tuple, int, float)):
                        value = str(value)
                    metadata[tag_name] = value
                
                if metadata:
                    logger.debug("Metadatos extraídos con éxito usando PIL")
                    return format_metadata(metadata)
            
            # Si no se encontraron metadatos
            logger.debug("No se encontraron metadatos")
            return {
                'warning': 'No se encontraron metadatos EXIF',
                'detalles': 'La imagen podría no contener metadatos EXIF o estar en un formato diferente.',
                'info_archivo': {
                    'formato': image.format,
                    'tamaño': os.path.getsize(image_path),
                    'modo': image.mode,
                    'dimensiones': image.size,
                    'nombre': os.path.basename(image_path)
                }
            }

    except Exception as e:
        logger.error(f"Error al procesar la imagen: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'detalles': 'Error al procesar los metadatos de la imagen',
            'info_archivo': {
                'tamaño': os.path.getsize(image_path),
                'nombre': os.path.basename(image_path)
            }
        }

def format_metadata(metadata):
    """
    Formatea los metadatos para una mejor presentación.
    
    Args:
        metadata: Dict con metadatos crudos
        
    Returns:
        dict: Metadatos formateados y organizados
    """
    formatted = {
        'información_básica': {},
        'información_técnica': {},
        'información_gps': {},
        'otros': {}
    }
    
    # Mapeo de campos comunes
    basic_fields = {'Make', 'Model', 'Software', 'DateTime', 'Artist', 'Copyright'}
    technical_fields = {'ExifImageWidth', 'ExifImageHeight', 'XResolution', 'YResolution', 
                       'ExposureTime', 'FNumber', 'ISOSpeedRatings', 'FocalLength'}
    gps_fields = {'GPSLatitude', 'GPSLongitude', 'GPSAltitude', 'GPSTimeStamp'}
    
    for key, value in metadata.items():
        if key in basic_fields:
            formatted['información_básica'][key] = value
        elif key in technical_fields:
            formatted['información_técnica'][key] = value
        elif key in gps_fields:
            formatted['información_gps'][key] = value
        else:
            formatted['otros'][key] = value
    
    return formatted

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)