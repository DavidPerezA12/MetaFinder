from flask import Flask, request, jsonify, send_from_directory
from PIL import Image
import piexif
from werkzeug.utils import secure_filename
import os

app = Flask(__name__, static_folder='../frontend', static_url_path='/static')
app.config['UPLOAD_FOLDER'] = 'uploads/'

@app.route('/')
def home():
    return send_from_directory('../frontend/html', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        metadata = extract_metadata(filepath)
        return jsonify(metadata)

def extract_metadata(image_path):
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if exif_data is not None:
            return {TAGS.get(tag): value for tag, value in exif_data.items()}
        else:
            return {'error': 'No EXIF data found'}
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)