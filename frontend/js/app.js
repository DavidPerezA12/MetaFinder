document.addEventListener('DOMContentLoaded', function() {
    const MetaFinder = {
        elements: {
            form: document.getElementById('uploadForm'),
            fileInput: document.getElementById('imageInput'),
            dropZone: document.getElementById('dropZone'),
            metadataDisplay: document.getElementById('metadata'),
            loadingIndicator: document.getElementById('loadingIndicator')
        },

        state: {
            isLoading: false,
            error: null,
            metadata: null
        },

        init() {
            this.bindEvents();
            this.setupDragAndDrop();
        },

        bindEvents() {
            this.elements.form.addEventListener('submit', this.handleSubmit.bind(this));
            this.elements.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        },

        setupDragAndDrop() {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                this.elements.dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });

            this.elements.dropZone.addEventListener('drop', this.handleDrop.bind(this));
            this.elements.dropZone.addEventListener('dragover', () => {
                this.elements.dropZone.classList.add('dragover');
            });
            this.elements.dropZone.addEventListener('dragleave', () => {
                this.elements.dropZone.classList.remove('dragover');
            });
        },

        async handleSubmit(event) {
            event.preventDefault();
            if (!this.elements.fileInput.files.length) {
                this.showError('Por favor, selecciona una imagen.');
                return;
            }
            await this.uploadFile(this.elements.fileInput.files[0]);
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
                this.validateAndPreviewFile(file);
                this.elements.fileInput.files = event.dataTransfer.files;
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
                const preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        },

        async uploadFile(file) {
            this.setState({ isLoading: true, error: null });
            
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
                this.setState({ isLoading: false });
            }
        },

        displayMetadata(metadata) {
            const formatted = this.formatMetadataDisplay(metadata);
            this.elements.metadataDisplay.innerHTML = formatted;
        },

        formatMetadataDisplay(metadata) {
            if (metadata.error) {
                return `<div class="error">${metadata.error}</div>`;
            }
            
            return `
                <div class="metadata-container">
                    ${Object.entries(metadata).map(([section, data]) => `
                        <div class="metadata-section">
                            <h3>${this.formatSectionTitle(section)}</h3>
                            <div class="metadata-content">
                                ${Object.entries(data).map(([key, value]) => `
                                    <div class="metadata-item">
                                        <span class="metadata-key">${this.formatKey(key)}:</span>
                                        <span class="metadata-value">${this.formatValue(value)}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        },

        formatSectionTitle(section) {
            return section.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        },

        formatKey(key) {
            return key.replace(/([A-Z])/g, ' $1