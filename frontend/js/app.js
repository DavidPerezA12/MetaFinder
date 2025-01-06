document.addEventListener('DOMContentLoaded', function() {
    const MetaFinder = {
        elements: {
            form: document.getElementById('uploadForm'),
            fileInput: document.getElementById('imageInput'),
            dropZone: document.getElementById('dropZone'),
            previewContainer: document.getElementById('previewContainer'),
            imagePreview: document.getElementById('imagePreview'),
            analyzeButton: document.getElementById('analyzeButton'),
            loadingIndicator: document.getElementById('loadingIndicator'),
            resultSection: document.getElementById('resultSection'),
            basicInfo: document.getElementById('basicInfo').querySelector('.metadata-content'),
            technicalInfo: document.getElementById('technicalInfo').querySelector('.metadata-content'),
            gpsInfo: document.getElementById('gpsInfo').querySelector('.metadata-content'),
            otherInfo: document.getElementById('otherInfo').querySelector('.metadata-content')
        },

        init() {
            this.bindEvents();
            this.setupDragAndDrop();
        },

        bindEvents() {
            this.elements.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
            this.elements.analyzeButton.addEventListener('click', this.handleAnalyze.bind(this));
        },

        setupDragAndDrop() {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                this.elements.dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });

            this.elements.dropZone.addEventListener('dragover', () => {
                this.elements.dropZone.classList.add('dragover');
            });

            this.elements.dropZone.addEventListener('dragleave', () => {
                this.elements.dropZone.classList.remove('dragover');
            });

            this.elements.dropZone.addEventListener('drop', this.handleDrop.bind(this));
        },

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.validateAndPreviewFile(file);
            }
        },

        handleDrop(event) {
            const file = event.dataTransfer.files[0];
            if (file) {
                this.elements.fileInput.files = event.dataTransfer.files;
                this.validateAndPreviewFile(file);
            }
            this.elements.dropZone.classList.remove('dragover');
        },

        validateAndPreviewFile(file) {
            if (!file.type.startsWith('image/')) {
                this.showError('Por favor, selecciona un archivo de imagen válido.');
                return false;
            }
            
            if (file.size > 16 * 1024 * 1024) {
                this.showError('El archivo es demasiado grande. El tamaño máximo es 16MB.');
                return false;
            }
            
            this.previewImage(file);
            return true;
        },

        previewImage(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.elements.imagePreview.src = e.target.result;
                this.elements.previewContainer.classList.remove('hidden');
                this.elements.resultSection.classList.add('hidden');
            };
            reader.readAsDataURL(file);
        },

        async handleAnalyze(event) {
            event.preventDefault();
            
            if (!this.elements.fileInput.files.length) {
                this.showError('Por favor, selecciona una imagen primero.');
                return;
            }

            await this.uploadFile(this.elements.fileInput.files[0]);
        },

        async uploadFile(file) {
            this.setLoading(true);
            
            const formData = new FormData();
            formData.append('image', file);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`Error HTTP: ${response.status}`);
                }
                
                const metadata = await response.json();
                this.displayMetadata(metadata);
                
            } catch (error) {
                this.showError(`Error al procesar la imagen: ${error.message}`);
            } finally {
                this.setLoading(false);
            }
        },

        setLoading(isLoading) {
            this.elements.loadingIndicator.classList.toggle('hidden', !isLoading);
            this.elements.analyzeButton.disabled = isLoading;
        },

        displayMetadata(metadata) {
            if (metadata.error || metadata.warning) {
                this.showError(metadata.error || metadata.warning);
                return;
            }

            // Limpiar contenedores
            this.elements.basicInfo.innerHTML = '';
            this.elements.technicalInfo.innerHTML = '';
            this.elements.gpsInfo.innerHTML = '';
            this.elements.otherInfo.innerHTML = '';

            // Mostrar datos por categoría con explicaciones
            if (metadata.información_básica && Object.keys(metadata.información_básica).length > 0) {
                this.elements.basicInfo.innerHTML = '<p>Datos generales sobre el archivo, como el nombre, tamaño y tipo.</p>';
                this.renderMetadataSection(metadata.información_básica, this.elements.basicInfo);
            } else {
                this.elements.basicInfo.innerHTML = '<p>No hay información básica disponible.</p>';
            }

            if (metadata.información_técnica && Object.keys(metadata.información_técnica).length > 0) {
                this.elements.technicalInfo.innerHTML = '<p>Detalles técnicos del archivo, como la resolución, el formato y la duración.</p>';
                this.renderMetadataSection(metadata.información_técnica, this.elements.technicalInfo);
            } else {
                this.elements.technicalInfo.innerHTML = '<p>No hay información técnica disponible.</p>';
            }

            if (metadata.información_gps && Object.keys(metadata.información_gps).length > 0) {
                this.elements.gpsInfo.innerHTML = '<p>Información de geolocalización, como la latitud, longitud y altitud.</p>';
                this.renderMetadataSection(metadata.información_gps, this.elements.gpsInfo);
            } else {
                this.elements.gpsInfo.innerHTML = '<p>No hay datos GPS disponibles.</p>';
            }

            if (metadata.otros && Object.keys(metadata.otros).length > 0) {
                this.elements.otherInfo.innerHTML = '<p>Información adicional que no encaja en las categorías anteriores.</p>';
                this.renderMetadataSection(metadata.otros, this.elements.otherInfo);
            } else {
                this.elements.otherInfo.innerHTML = '<p>No hay otros metadatos disponibles.</p>';
            }

            this.elements.resultSection.classList.remove('hidden');
            this.elements.resultSection.scrollIntoView({ behavior: 'smooth' });
        },

        renderMetadataSection(data, container) {
            Object.entries(data).forEach(([key, value]) => {
                const item = document.createElement('div');
                item.className = 'metadata-item';
                item.innerHTML = `
                    <span class="metadata-key">${this.formatKey(key)}</span>
                    <span class="metadata-value">${this.formatValue(value)}</span>
                `;
                container.appendChild(item);
            });
        },

        formatKey(key) {
            return key
                .replace(/([A-Z])/g, ' $1')
                .replace(/_/g, ' ')
                .trim()
                .replace(/\b\w/g, l => l.toUpperCase());
        },

        formatValue(value) {
            if (value === null || value === undefined) {
                return 'No disponible';
            }
            if (typeof value === 'object') {
                return JSON.stringify(value, null, 2);
            }
            return String(value);
        },

        showError(message) {
            alert(message);
        }
    };

    MetaFinder.init();
});