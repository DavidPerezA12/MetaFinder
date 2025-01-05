import pytest
import os
from app import app, extract_metadata, allowed_file
from PIL import Image
import io

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def create_test_image():
    """Crea una imagen de prueba con metadatos EXIF básicos."""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io

def test_allowed_file():
    """Prueba la validación de extensiones de archivo."""
    assert allowed_file('test.jpg') == True
    assert allowed_file('test.png') == True
    assert allowed_file('test.txt') == False
    assert allowed_file('test') == False

def test_upload_without_file(client):
    """Prueba el intento de subida sin archivo."""
    response = client.post('/upload')
    assert response.status_code == 400
    assert b'error' in response.data

def test_upload_with_valid_image(client):
    """Prueba la subida de una imagen válida."""
    img_io = create_test_image()
    data = {'image': (img_io, 'test.jpg')}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200

def test_extract_metadata_with_invalid_file():
    """Prueba la extracción de metadatos de un archivo inválido."""
    with pytest.raises(Exception):
        extract_metadata('nonexistent.jpg')