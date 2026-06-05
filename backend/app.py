import hashlib
import logging
import mimetypes
import os
import tempfile
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

try:
    from .scripts.processor import extract_metadata, ImageProcessingError
except ImportError:
    from scripts.processor import extract_metadata, ImageProcessingError

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / 'frontend'
UPLOAD_DIR = Path(os.environ.get('UPLOAD_DIR', '/tmp/metafinder-uploads'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_FILE = os.environ.get('LOG_FILE')
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('ALLOWED_ORIGINS', '').split(',')
    if origin.strip()
]

log_handlers = [logging.StreamHandler()]
if LOG_FILE:
    log_handlers.append(logging.FileHandler(LOG_FILE))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

try:
    import magic
except ImportError:
    magic = None

MAX_UPLOAD_BYTES = 16 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'webp'}

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path='/static')
if ALLOWED_ORIGINS:
    CORS(app, resources={r"/upload": {"origins": ALLOWED_ORIGINS}})

app.config.update(
    UPLOAD_FOLDER=str(UPLOAD_DIR),
    MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
    ALLOWED_EXTENSIONS=ALLOWED_EXTENSIONS,
    SECRET_KEY=os.environ.get('SECRET_KEY') or os.urandom(32)
)

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


@app.after_request
def add_security_headers(response):
    response.headers.setdefault('Content-Security-Policy', (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    ))
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    return response


class FileTypeNotAllowedError(Exception):
    pass


class FileIntegrityError(Exception):
    pass


class EmptyFileError(Exception):
    pass


class ImageTooLargeError(Exception):
    pass


def allowed_file(filename: str) -> bool:
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    )


def json_error(message: str, status_code: int):
    response = jsonify({'error': message, 'status': status_code})
    response.status_code = status_code
    return response


def format_bytes(size_bytes: int) -> str:
    units = ('B', 'KB', 'MB', 'GB')
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f'{int(size)} {units[unit_index]}'
    return f'{size:.2f} {units[unit_index]}'


def normalize_upload_filename(filename: str) -> tuple[str, str]:
    if not allowed_file(filename):
        raise FileTypeNotAllowedError('File type is not allowed')

    extension = filename.rsplit('.', 1)[1].lower()
    safe_name = secure_filename(filename)

    if not safe_name or '.' not in safe_name:
        safe_name = f'image.{extension}'
    elif safe_name.rsplit('.', 1)[1].lower() not in app.config['ALLOWED_EXTENSIONS']:
        safe_name = f"{safe_name.rsplit('.', 1)[0]}.{extension}"

    return safe_name, extension


def detect_mime_type(filepath: str) -> Optional[str]:
    if not magic:
        return None

    try:
        mime_type = magic.from_file(filepath, mime=True)
        logger.debug(f"Detected MIME type: {mime_type}")
        return mime_type
    except Exception as e:
        logger.warning(f"Error detecting MIME type: {str(e)}")
        return None


def verify_with_pillow(filepath: str) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(filepath) as img:
            img.verify()


def validate_image_type(filepath: str) -> bool:
    try:
        mime_type = detect_mime_type(filepath)
        if mime_type:
            return mime_type.startswith('image/')

        verify_with_pillow(filepath)
        logger.debug("Image type validated with Pillow")
        return True
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        logger.warning(f"File rejected because it is too large to process safely: {str(e)}")
        raise ImageTooLargeError('The image is too large to process safely') from e
    except Exception as e:
        logger.warning(f"File rejected during type validation: {str(e)}")
        return False


def get_file_hash(file_path: str) -> str:
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error generating hash: {str(e)}")
        raise FileIntegrityError("Could not verify file integrity")


def validate_image_integrity(filepath: str) -> bool:
    try:
        verify_with_pillow(filepath)
        return True
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        logger.warning(f"File rejected because it is too large to process safely: {str(e)}")
        raise ImageTooLargeError('The image is too large to process safely') from e
    except Exception as e:
        logger.warning(f"File rejected during integrity validation: {str(e)}")
        return False


def build_file_info(filepath: str, filename: str, extension: str, file_hash: str) -> dict:
    size_bytes = os.path.getsize(filepath)
    processed_at = datetime.now().isoformat()
    guessed_mime_type, _ = mimetypes.guess_type(filename)
    return {
        'hash': file_hash,
        'timestamp': processed_at,
        'processed_at': processed_at,
        'filename': filename,
        'extension': extension,
        'mime_type': detect_mime_type(filepath) or guessed_mime_type or 'image/unknown',
        'size': size_bytes,
        'size_bytes': size_bytes,
        'size_human': format_bytes(size_bytes),
    }


@app.route('/')
def home():
    try:
        return send_from_directory(FRONTEND_DIR / 'html', 'index.html')
    except Exception as e:
        logger.error(f"Error serving frontend: {str(e)}")
        return json_error('Could not load the page', 500)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'MetaFinder',
        'max_upload_bytes': app.config['MAX_CONTENT_LENGTH'],
        'max_image_pixels': Image.MAX_IMAGE_PIXELS,
        'allowed_extensions': sorted(app.config['ALLOWED_EXTENSIONS']),
    })


@app.route('/upload', methods=['POST'])
def upload_image():
    filepath = None
    try:
        if 'image' not in request.files:
            raise ValueError('No image was provided')
        
        file = request.files['image']
        if file.filename == '':
            raise ValueError('No file was selected')
            
        filename, extension = normalize_upload_filename(file.filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=app.config['UPLOAD_FOLDER'],
            suffix=f'.{extension}'
        ) as tmp:
            filepath = tmp.name

        file.save(filepath)
        logger.debug(f"File saved at: {filepath}")

        if os.path.getsize(filepath) == 0:
            raise EmptyFileError('The file is empty')

        if not validate_image_type(filepath):
            raise FileTypeNotAllowedError('The file is not a valid image')

        if not validate_image_integrity(filepath):
            raise FileIntegrityError('The image is corrupt or invalid')
        
        file_hash = get_file_hash(filepath)
        metadata = extract_metadata(filepath)
        metadata['file_info'] = build_file_info(filepath, filename, extension, file_hash)
        
        return jsonify(metadata)

    except (ValueError, FileTypeNotAllowedError) as e:
        logger.warning(f"Validation error: {str(e)}")
        return json_error(str(e), 400)
    except EmptyFileError as e:
        logger.warning(f"Empty file: {str(e)}")
        return json_error(str(e), 422)
    except ImageTooLargeError as e:
        logger.warning(f"Image too large: {str(e)}")
        return json_error(str(e), 422)
    except (FileIntegrityError, ImageProcessingError) as e:
        logger.error(f"Processing error: {str(e)}")
        return json_error(str(e), 422)
    except RequestEntityTooLarge:
        logger.warning("File too large")
        return json_error('The file exceeds the maximum allowed size', 413)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return json_error('Internal server error', 500)
    finally:
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.debug(f"Temporary file removed: {filepath}")
            except Exception as e:
                logger.error(f"Error removing temporary file: {str(e)}")


@app.errorhandler(400)
def bad_request_error(error):
    return json_error(str(error.description), 400)


@app.errorhandler(413)
def request_entity_too_large_error(error):
    return json_error('The file exceeds the maximum allowed size', 413)


@app.errorhandler(422)
def unprocessable_entity_error(error):
    return json_error(str(error.description), 422)


@app.errorhandler(500)
def internal_error(error):
    return json_error(str(error.description), 500)


if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    app.run(debug=debug)
