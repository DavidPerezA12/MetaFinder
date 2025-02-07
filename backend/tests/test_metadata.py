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

def create_test_image_with_gps():
    """Crea una imagen de prueba con metadatos EXIF incluyendo datos GPS."""
    img = Image.new('RGB', (100, 100), color='red')
    exif_data = {
        34853: {  # GPSInfo tag
            1: 'N',  # GPSLatitudeRef
            2: ((40, 1), (44, 1), (55, 1)),  # GPSLatitude
            3: 'W',  # GPSLongitudeRef
            4: ((73, 1), (59, 1), (7, 1))  # GPSLongitude
        }
    }
    img.info['exif'] = piexif.dump({'GPS': exif_data})
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', exif=img.info['exif'])
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

def test_extract_metadata_with_gps():
    """Prueba la extracción de metadatos de una imagen con datos GPS."""
    img_io = create_test_image_with_gps()
    img_path = '/tmp/test_image_with_gps.jpg'
    with open(img_path, 'wb') as f:
        f.write(img_io.getbuffer())
    
    metadata = extract_metadata(img_path)
    
    assert 'información_gps' in metadata
    gps_info = metadata['información_gps']
    assert 'GPSDecimalLatitude' in gps_info
    assert 'GPSDecimalLongitude' in gps_info
    assert gps_info['GPSDecimalLatitude'] == 40.748611  # Valor esperado
    assert gps_info['GPSDecimalLongitude'] == -73.985278  # Valor esperado

    os.remove(img_path)

if __name__ == '__main__':
    pytest.main()