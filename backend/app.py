import os
import logging
import hashlib
import magic
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from PIL import Image
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from typing import Dict, Any, Optional

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
CORS(app)

# Configuración
app.config.update(
    UPLOAD_FOLDER=os.path.abspath('uploads/'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'webp'},
    SECRET_KEY=os.environ.get('SECRET_KEY', 'default-secret-key')
)

class FileTypeNotAllowedError(Exception):
    """Excepción personalizada cuando el archivo no es de tipo permitido."""
    pass

class FileIntegrityError(Exception):
    """Excepción personalizada para errores de integridad del archivo."""
    pass

def allowed_file(filename: str) -> bool:
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_image_type(filepath: str) -> bool:
    """Valida el tipo MIME del archivo usando python-magic."""
    try:
        mime_type = magic.from_file(filepath, mime=True)
        logger.debug(f"Tipo MIME detectado: {mime_type}")
        return mime_type.startswith('image/')
    except Exception as e:
        logger.error(f"Error al validar tipo MIME: {str(e)}")
        return False

def get_file_hash(file_path: str) -> str:
    """Genera un hash SHA-256 del archivo."""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error al generar hash: {str(e)}")
        raise FileIntegrityError("Error al verificar la integridad del archivo")

def validate_image_integrity(filepath: str) -> bool:
    """Valida la integridad de la imagen usando PIL."""
    try:
        with Image.open(filepath) as img:
            img.verify()
        return True
    except Exception as e:
        logger.error(f"Error de integridad de imagen: {str(e)}")
        return False

@app.route('/')
def home():
    """Ruta principal que sirve el frontend."""
    try:
        return send_from_directory('../frontend/html', 'index.html')
    except Exception as e:
        logger.error(f"Error al servir frontend: {str(e)}")
        return jsonify({'error': 'Error al cargar la página'}), 500

@app.route('/upload', methods=['POST'])
def upload_image():
    """Procesa la subida de imágenes y extrae sus metadatos."""
    filepath = None
    try:
        if 'image' not in request.files:
            raise ValueError('No se proporcionó ninguna imagen')
        
        file = request.files['image']
        if file.filename == '':
            raise ValueError('No se seleccionó ningún archivo')
            
        if not allowed_file(file.filename):
            raise FileTypeNotAllowedError('Tipo de archivo no permitido')
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        logger.debug(f"Archivo guardado en: {filepath}")

        if not validate_image_type(filepath):
            raise FileTypeNotAllowedError('El archivo no corresponde a una imagen válida')

        if not validate_image_integrity(filepath):
            raise FileIntegrityError('La imagen está corrupta o no es válida')
        
        file_hash = get_file_hash(filepath)
        metadata = extract_metadata(filepath)
        
        metadata['file_info'] = {
            'hash': file_hash,
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'size': os.path.getsize(filepath)
        }
        
        return jsonify(metadata)

    except (ValueError, FileTypeNotAllowedError) as e:
        logger.warning(f"Error de validación: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except (FileIntegrityError, ImageProcessingError) as e:
        logger.error(f"Error de procesamiento: {str(e)}")
        return jsonify({'error': str(e)}), 422
    except RequestEntityTooLarge:
        logger.warning("Archivo demasiado grande")
        return jsonify({'error': 'El archivo excede el tamaño máximo permitido'}), 413
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.debug(f"Archivo temporal eliminado: {filepath}")
            except Exception as e:
                logger.error(f"Error al eliminar archivo temporal: {str(e)}")

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({'error': str(error.description)}), 400

@app.errorhandler(413)
def request_entity_too_large_error(error):
    return jsonify({'error': 'El archivo excede el tamaño máximo permitido'}), 413

@app.errorhandler(422)
def unprocessable_entity_error(error):
    return jsonify({'error': str(error.description)}), 422

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': str(error.description)}), 500

if __name__ == '__main__':
    app.run(debug=True)
