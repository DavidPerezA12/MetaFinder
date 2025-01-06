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

            // Mostrar datos por categoría
            if (metadata.información_básica) {
                this.renderMetadataSection(metadata.información_básica, this.elements.basicInfo);
            }
            
            if (metadata.información_técnica) {
                this.renderMetadataSection(metadata.información_técnica, this.elements.technicalInfo);
            }
            
            if (metadata.información_gps) {
                this.renderMetadataSection(metadata.información_gps, this.elements.gpsInfo);
            }
            
            if (metadata.otros) {
                this.renderMetadataSection(metadata.otros, this.elements.otherInfo);
            }

            // Ejemplo: Si quisieras mostrar la info del archivo
            if (metadata.file_info) {
                const fileInfo = metadata.file_info;
                const item = document.createElement('div');
                item.className = 'metadata-item';
                item.innerHTML = `
                    <span class="metadata-key">Hash (SHA-256)</span>
                    <span class="metadata-value">${fileInfo.hash}</span>
                `;
                this.elements.otherInfo.appendChild(item);

                // Puedes mostrar más datos como filename, size, timestamp, etc.
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
