import io
import os
import tempfile

import piexif
import pytest
from PIL import Image

from app import app, allowed_file, extract_metadata, format_bytes, normalize_upload_filename


@pytest.fixture
def client(tmp_path):
    app.config.update(
        TESTING=True,
        UPLOAD_FOLDER=str(tmp_path),
    )
    with app.test_client() as client:
        yield client


def create_test_image(image_format='JPEG', exif=None):
    img = Image.new('RGB', (100, 100), color='red')
    img_io = io.BytesIO()
    save_kwargs = {}
    if exif:
        save_kwargs['exif'] = piexif.dump(exif)
    img.save(img_io, image_format, **save_kwargs)
    img_io.seek(0)
    return img_io


def gps_exif():
    return {
        'GPS': {
            piexif.GPSIFD.GPSLatitudeRef: b'N',
            piexif.GPSIFD.GPSLatitude: ((40, 1), (44, 1), (55, 1)),
            piexif.GPSIFD.GPSLongitudeRef: b'W',
            piexif.GPSIFD.GPSLongitude: ((73, 1), (59, 1), (7, 1)),
            piexif.GPSIFD.GPSAltitude: (42, 1),
        }
    }


def gps_exif_with_broken_zoom():
    exif = gps_exif()
    exif['Exif'] = {
        piexif.ExifIFD.DigitalZoomRatio: (1, 0),
    }
    return exif


def test_allowed_file():
    assert allowed_file('test.jpg') is True
    assert allowed_file('test.png') is True
    assert allowed_file('test.webp') is True
    assert allowed_file('test.txt') is False
    assert allowed_file('test') is False


@pytest.mark.parametrize(
    ('size_bytes', 'expected'),
    [
        (0, '0 B'),
        (512, '512 B'),
        (1536, '1.50 KB'),
        (2 * 1024 * 1024, '2.00 MB'),
    ],
)
def test_format_bytes(size_bytes, expected):
    assert format_bytes(size_bytes) == expected


@pytest.mark.parametrize(
    ('original_name', 'safe_name', 'extension'),
    [
        ('.jpg', 'image.jpg', 'jpg'),
        ('💩.jpg', 'image.jpg', 'jpg'),
        ('a.b.jpg', 'a.b.jpg', 'jpg'),
    ],
)
def test_normalize_upload_filename_keeps_valid_extension(original_name, safe_name, extension):
    assert normalize_upload_filename(original_name) == (safe_name, extension)


def test_upload_without_file(client):
    response = client.post('/upload')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'No image was provided'


def test_health_endpoint_reports_service_config(client):
    response = client.get('/health')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['status'] == 'ok'
    assert payload['service'] == 'MetaFinder'
    assert payload['max_upload_bytes'] == 16 * 1024 * 1024
    assert payload['max_image_pixels'] == 50_000_000
    assert 'jpg' in payload['allowed_extensions']


def test_upload_rejects_invalid_extension(client):
    response = client.post(
        '/upload',
        data={'image': (io.BytesIO(b'not an image'), 'note.txt')},
        content_type='multipart/form-data',
    )
    assert response.status_code == 400
    assert response.get_json()['error'] == 'File type is not allowed'


def test_upload_rejects_empty_image_file(client):
    response = client.post(
        '/upload',
        data={'image': (io.BytesIO(b''), 'empty.jpg')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 422
    assert response.get_json()['error'] == 'The file is empty'


def test_upload_with_valid_image_returns_metadata_and_cleans_tmp_file(client, tmp_path):
    img_io = create_test_image()

    response = client.post(
        '/upload',
        data={'image': (img_io, 'test.jpg')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    metadata = response.get_json()
    assert metadata['basic_info']['Format'] == 'JPEG'
    assert metadata['basic_info']['Dimensions'] == '100 x 100'
    assert metadata['technical_info']['Aspect ratio'] == '1:1'
    assert metadata['technical_info']['Channels'] == 3
    assert metadata['file_info']['filename'] == 'test.jpg'
    assert metadata['file_info']['extension'] == 'jpg'
    assert metadata['file_info']['size_bytes'] == metadata['file_info']['size']
    assert metadata['file_info']['size_human'].endswith('B')
    assert metadata['file_info']['mime_type'].startswith('image/')
    assert metadata['file_info']['processed_at']
    assert metadata['file_info']['hash']
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_image_that_exceeds_safe_pixel_limit(client, monkeypatch):
    monkeypatch.setattr(Image, 'MAX_IMAGE_PIXELS', 1)

    response = client.post(
        '/upload',
        data={'image': (create_test_image(), 'too-large.jpg')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 422
    assert response.get_json()['error'] == 'The image is too large to process safely'


def test_upload_with_same_filename_does_not_collide(client):
    for _ in range(2):
        response = client.post(
            '/upload',
            data={'image': (create_test_image(), 'same-name.jpg')},
            content_type='multipart/form-data',
        )
        assert response.status_code == 200
        assert response.get_json()['file_info']['filename'] == 'same-name.jpg'


def test_upload_with_dot_filename_does_not_500(client):
    response = client.post(
        '/upload',
        data={'image': (create_test_image(), '.jpg')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.get_json()['file_info']['filename'] == 'image.jpg'


def test_extract_metadata_with_invalid_file():
    with pytest.raises(Exception):
        extract_metadata('nonexistent.jpg')


def test_extract_metadata_with_gps():
    img_io = create_test_image(exif=gps_exif())

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(img_io.getbuffer())
        img_path = tmp.name

    try:
        metadata = extract_metadata(img_path)
    finally:
        os.remove(img_path)

    gps_info = metadata['gps_info']
    assert gps_info['Latitude'] == '40.748611° N'
    assert gps_info['Longitude'] == '73.985278° W'
    assert gps_info['Decimal coordinates']['latitude'] == pytest.approx(40.748611)
    assert gps_info['Decimal coordinates']['longitude'] == pytest.approx(-73.985278)
    assert gps_info['Altitude'] == '42.0 meters'


def test_extract_metadata_keeps_gps_when_one_exif_tag_is_invalid():
    img_io = create_test_image(exif=gps_exif_with_broken_zoom())

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(img_io.getbuffer())
        img_path = tmp.name

    try:
        metadata = extract_metadata(img_path)
    finally:
        os.remove(img_path)

    assert 'Digital zoom' not in metadata['advanced_info']
    assert metadata['gps_info']['Latitude'] == '40.748611° N'
    assert metadata['gps_info']['Longitude'] == '73.985278° W'


def test_extract_metadata_keeps_exif_text_as_data():
    exif = {
        '0th': {
            piexif.ImageIFD.Make: b'<img src=x onerror=alert(1)>',
        }
    }
    img_io = create_test_image(exif=exif)

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(img_io.getbuffer())
        img_path = tmp.name

    try:
        metadata = extract_metadata(img_path)
    finally:
        os.remove(img_path)

    assert metadata['basic_info']['Make'] == '<img src=x onerror=alert(1)>'


def test_extract_metadata_includes_unmapped_exif_tags():
    exif = {
        '0th': {
            piexif.ImageIFD.DateTime: b'2026:06:05 12:00:00',
        },
        'Exif': {
            piexif.ExifIFD.ColorSpace: 1,
            piexif.ExifIFD.DateTimeDigitized: b'2026:06:05 12:00:01',
        },
    }
    img_io = create_test_image(exif=exif)

    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(img_io.getbuffer())
        img_path = tmp.name

    try:
        metadata = extract_metadata(img_path)
    finally:
        os.remove(img_path)

    extra_exif = metadata['other_info']['Unmapped EXIF']
    assert extra_exif['0th']['DateTime'] == '2026:06:05 12:00:00'
    assert extra_exif['Exif']['ColorSpace'] == 1
    assert extra_exif['Exif']['DateTimeDigitized'] == '2026:06:05 12:00:01'


def test_extract_metadata_includes_png_textual_metadata():
    img = Image.new('RGB', (80, 40), color='blue')
    img_io = io.BytesIO()
    from PIL.PngImagePlugin import PngInfo

    png_info = PngInfo()
    png_info.add_text('Author', 'MetaFinder Test')
    png_info.add_text('Description', 'Embedded text')
    img.save(img_io, 'PNG', pnginfo=png_info)
    img_io.seek(0)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp.write(img_io.getbuffer())
        img_path = tmp.name

    try:
        metadata = extract_metadata(img_path)
    finally:
        os.remove(img_path)

    format_metadata = metadata['other_info']['Format metadata']
    assert format_metadata['Author'] == 'MetaFinder Test'
    assert format_metadata['Description'] == 'Embedded text'
