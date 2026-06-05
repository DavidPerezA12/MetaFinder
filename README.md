# MetaFinder

[![CI](https://github.com/DavidPerezA12/MetaFinder/actions/workflows/ci.yml/badge.svg)](https://github.com/DavidPerezA12/MetaFinder/actions/workflows/ci.yml)

MetaFinder is a small web app for inspecting image metadata. Drop in an image and it will show the useful bits: format, dimensions, EXIF camera data, GPS coordinates when present, file size, MIME type, and a SHA-256 hash.

It is meant to be simple to run, easy to read, and honest about what is actually inside the file. If a photo has had its EXIF stripped by a social network or messaging app, MetaFinder will show empty sections instead of guessing.

The current scope is intentionally small and feature-complete: upload one image, inspect it, and export clean JSON.

## What It Checks

- Image format, dimensions, color mode, resolution, aspect ratio, channels, and DPI.
- EXIF camera data such as make, model, lens, ISO, aperture, exposure time, flash, and capture settings.
- GPS latitude, longitude, decimal coordinates, and altitude when available.
- Extra EXIF tags that are not part of the main display groups.
- Text metadata embedded in formats such as PNG.
- File integrity details, including SHA-256 hash, detected MIME type, extension, and size.

Supported formats: JPG, JPEG, PNG, GIF, TIFF, BMP, and WEBP.

Maximum upload size: 16 MB.
Images above 50 million decoded pixels are rejected before metadata extraction.

## Running Locally

You need Python 3.10 or newer. On some systems, `python-magic` also needs the native `libmagic` library.

On macOS:

```bash
brew install libmagic
```

Then run:

```bash
git clone https://github.com/DavidPerezA12/MetaFinder.git
cd MetaFinder
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 backend/app.py
```

Open:

```text
http://localhost:5000
```

For local debug mode:

```bash
FLASK_DEBUG=1 python3 backend/app.py
```

## Tests

```bash
pip install -r backend/requirements-dev.txt
python3 -m pytest
```

The GitHub Actions workflow runs the same suite on Python 3.10 and 3.12.

## Privacy And Safety

- Uploaded files are saved to a temporary directory only for the current request.
- Temporary files are deleted after processing, including failed requests.
- The app does not persist images or extracted metadata.
- Responses include a SHA-256 hash so results can be tied back to the exact file that was inspected.

## API

### `GET /health`

Returns a basic service check and public upload limits.

```json
{
  "status": "ok",
  "service": "MetaFinder",
  "max_upload_bytes": 16777216,
  "max_image_pixels": 50000000,
  "allowed_extensions": ["bmp", "gif", "jpeg", "jpg", "png", "tiff", "webp"]
}
```

### `POST /upload`

Upload one image using `multipart/form-data` with the field name `image`.

Example response:

```json
{
  "basic_info": {},
  "technical_info": {},
  "gps_info": {},
  "advanced_info": {},
  "other_info": {},
  "file_info": {
    "filename": "photo.jpg",
    "extension": "jpg",
    "mime_type": "image/jpeg",
    "size": 123456,
    "size_bytes": 123456,
    "size_human": "120.56 KB",
    "hash": "sha256...",
    "timestamp": "2026-06-05T12:00:00.000000",
    "processed_at": "2026-06-05T12:00:00.000000"
  }
}
```

Error responses:

- `400`: missing file, empty filename, unsupported extension, or invalid image content.
- `413`: upload is larger than 16 MB.
- `422`: empty, corrupt, or unprocessable image.
- `500`: unexpected server error.

## Configuration

- `SECRET_KEY`: Flask secret key.
- `FLASK_DEBUG=1`: enables debug mode for local development.
- `LOG_LEVEL`: logging level, for example `INFO` or `DEBUG`.
- `LOG_FILE`: optional log file path. If unset, logs go to stdout.
- `UPLOAD_DIR`: optional temporary upload directory. Defaults to `/tmp/metafinder-uploads`.
- `ALLOWED_ORIGINS`: comma-separated origins for CORS on `/upload` when the frontend is served elsewhere.

## Project Layout

```text
MetaFinder/
├── .python-version
├── .github/
│   └── workflows/
│       └── ci.yml
├── api/
│   └── index.py
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── scripts/
│   │   └── processor.py
│   └── tests/
│       └── test_metadata.py
├── frontend/
│   ├── css/
│   │   └── styles.css
│   ├── html/
│   │   └── index.html
│   ├── img/
│   └── js/
│       └── app.js
├── SECURITY.md
├── pytest.ini
├── requirements.txt
└── vercel.json
```

## License

MIT
