import os
import logging
import hashlib
import magic  # Para validación del tipo MIME
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from PIL import Image
from werkzeug.utils import secure_filename
from typing import Dict, Any

# Importamos la función de extracción de metadatos desde nuestro archivo separado
from scripts.processor import extract_metadata, ImageProcessingError

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../frontend', static_url_path='/static')
CORS(app)  # Habilitar CORS para desarrollo

# Configuración
app.config.update(
    UPLOAD_FOLDER='uploads/',
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp'},
    SECRET_KEY=os.environ.get('SECRET_KEY', 'default-secret-key')
)

class FileTypeNotAllowedError(Exception):
    """Excepción personalizada cuando el archivo no es de tipo permitido."""
    pass

def allowed_file(filename: str) -> bool:
    """
    Verifica si el archivo tiene una extensión permitida.
    
    Args:
        filename (str): Nombre del archivo a verificar
        
    Returns:
        bool: True si la extensión está permitida, False en caso contrario
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_image_type(filepath: str) -> bool:
    """
    Valida el tipo MIME del archivo usando python-magic.
    
    Args:
        filepath (str): Ruta del archivo a validar
        
    Returns:
        bool: True si es un tipo de imagen válido, de lo contrario False
    """
    mime_type = magic.from_file(filepath, mime=True)
    logger.debug(f"Tipo MIME detectado: {mime_type}")
    return mime_type.startswith('image/')

def get_file_hash(file_path: str) -> str:
    """
    Genera un hash SHA-256 del archivo.
    
    Args:
        file_path (str): Ruta al archivo
        
    Returns:
        str: Hash SHA-256 del archivo
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

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
        
        # Aseguramos la carpeta de uploads
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file.save(filepath)
        logger.debug(f"Archivo guardado en: {filepath}")

        # Validación adicional con python-magic
        if not validate_image_type(filepath):
            os.remove(filepath)
            return jsonify({'error': 'El archivo no corresponde a una imagen válida'}), 400
        
        try:
            file_hash = get_file_hash(filepath)
            
            # Llamamos a nuestra función de extracción de metadatos desde processor.py
            metadata = extract_metadata(filepath)
            
            # Agregar información adicional
            metadata['file_info'] = {
                'hash': file_hash,
                'timestamp': datetime.now().isoformat(),
                'filename': filename,
                'size': os.path.getsize(filepath)
            }
            
            return jsonify(metadata)
        finally:
            # Borramos el archivo temporal para no saturar el servidor
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Archivo temporal eliminado: {filepath}")
    
    except FileTypeNotAllowedError as e:
        logger.error(f"Error de tipo de archivo: {str(e)}", exc_info=True)
        return jsonify({'error': 'Tipo de archivo no permitido'}), 400
    except ImageProcessingError as e:
        logger.error(f"Error en el procesamiento de la imagen: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error al procesar la imagen'}), 500
    except Exception as e:
        logger.error(f"Error en upload_image: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({'error': str(error.description)}), 400

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': str(error.description)}), 500

if __name__ == '__main__':
   app.run(debug=True)
