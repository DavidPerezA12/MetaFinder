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
            otherInfo: document.getElementById('otherInfo').querySelector('.metadata-content'),
            errorContainer: document.getElementById('errorContainer') || (() => {
                const container = document.createElement('div');
                container.id = 'errorContainer';
                container.className = 'error-container hidden';
                document.querySelector('main').insertBefore(container, document.querySelector('#resultSection'));
                return container;
            })()
        },

        config: {
            maxFileSize: 16 * 1024 * 1024, // 16MB
            allowedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
            uploadEndpoint: '/upload'
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
            this.hideError();

            if (!this.config.allowedTypes.includes(file.type)) {
                this.showError('Por favor, selecciona un archivo de imagen válido (JPEG, PNG, GIF, o WEBP).');
                return false;
            }
            
            if (file.size > this.config.maxFileSize) {
                this.showError(`El archivo es demasiado grande. El tamaño máximo es ${this.formatFileSize(this.config.maxFileSize)}.`);
                return false;
            }
            
            this.previewImage(file);
            return true;
        },

        formatFileSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let size = bytes;
            let unitIndex = 0;
            
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            
            return `${size.toFixed(2)} ${units[unitIndex]}`;
        },

        previewImage(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.elements.imagePreview.src = e.target.result;
                this.elements.previewContainer.classList.remove('hidden');
                this.elements.resultSection.classList.add('hidden');
            };
            reader.onerror = () => {
                this.showError('Error al cargar la vista previa de la imagen.');
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
            this.hideError();
            
            const formData = new FormData();
            formData.append('image', file);
            
            try {
                const response = await fetch(this.config.uploadEndpoint, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || `Error HTTP: ${response.status}`);
                }
                
                this.displayMetadata(data);
                
            } catch (error) {
                this.showError(`Error al procesar la imagen: ${error.message}`);
                this.elements.resultSection.classList.add('hidden');
            } finally {
                this.setLoading(false);
            }
        },

        setLoading(isLoading) {
            this.elements.loadingIndicator.classList.toggle('hidden', !isLoading);
            this.elements.analyzeButton.disabled = isLoading;
            if (isLoading) {
                this.elements.dropZone.classList.add('processing');
            } else {
                this.elements.dropZone.classList.remove('processing');
            }
        },

        displayMetadata(metadata) {
            if (metadata.error || metadata.warning) {
                this.showError(metadata.error || metadata.warning);
                return;
            }

            // Limpiar contenedores
            Object.values(this.elements).forEach(element => {
                if (element.classList.contains('metadata-content')) {
                    element.innerHTML = '';
                }
            });

            // Mostrar datos por categoría con explicaciones
            this.renderMetadataCategory('información_básica', metadata, this.elements.basicInfo,
                'Datos generales sobre el archivo, como el nombre, tamaño y tipo.');

            this.renderMetadataCategory('información_técnica', metadata, this.elements.technicalInfo,
                'Detalles técnicos del archivo, como la resolución, el formato y la duración.');

            this.renderMetadataCategory('información_gps', metadata, this.elements.gpsInfo,
                'Información de geolocalización, como la latitud, longitud y altitud.');

            this.renderMetadataCategory('otros', metadata, this.elements.otherInfo,
                'Información adicional que no encaja en las categorías anteriores.');

            this.elements.resultSection.classList.remove('hidden');
            this.elements.resultSection.scrollIntoView({ behavior: 'smooth' });
        },

        renderMetadataCategory(category, metadata, container, description) {
            const data = metadata[category];
            if (data && Object.keys(data).length > 0) {
                container.innerHTML = `<p class="category-description">${description}</p>`;
                this.renderMetadataSection(data, container);
            } else {
                container.innerHTML = `<p class="no-data">No hay ${category.replace('_', ' ')} disponible.</p>`;
            }
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
            if (typeof value === 'number') {
                return value.toLocaleString();
            }
            return String(value);
        },

        showError(message) {
            this.elements.errorContainer.textContent = message;
            this.elements.errorContainer.classList.remove('hidden');
            this.elements.errorContainer.scrollIntoView({ behavior: 'smooth' });
        },

        hideError() {
            this.elements.errorContainer.classList.add('hidden');
            this.elements.errorContainer.textContent = '';
        }
    };

    MetaFinder.init();
});