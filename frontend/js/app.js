document.addEventListener('DOMContentLoaded', () => {
    const getElement = (id) => {
        const element = document.getElementById(id);
        if (!element) {
            throw new Error(`Missing required element: #${id}`);
        }
        return element;
    };

    const getMetadataContainer = (id) => {
        const container = getElement(id).querySelector('.metadata-content');
        if (!container) {
            throw new Error(`Missing metadata container: #${id} .metadata-content`);
        }
        return container;
    };
    const getActionKey = ({ key }) => (key === 'Enter' || key === ' ');
    const acceptedTypes = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/tiff', 'image/bmp', 'image/webp']);
    const acceptedExtensions = new Set(['jpg', 'jpeg', 'png', 'gif', 'tiff', 'bmp', 'webp']);
    const numberFormatter = new Intl.NumberFormat('en-US');
    const dateFormatter = new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short'
    });
    const keyLabels = {
        hash: 'Hash SHA-256',
        timestamp: 'Timestamp',
        processed_at: 'Processed at',
        filename: 'File name',
        extension: 'Extension',
        mime_type: 'MIME type',
        size: 'Size',
        size_bytes: 'Size in bytes',
        size_human: 'Readable size',
        latitude: 'Latitude',
        longitude: 'Longitude'
    };

    const MetaFinder = {
        elements: {
            form: getElement('uploadForm'),
            fileInput: getElement('imageInput'),
            dropZone: getElement('dropZone'),
            previewContainer: getElement('previewContainer'),
            imagePreview: getElement('imagePreview'),
            selectedFileSummary: getElement('selectedFileSummary'),
            analyzeButton: getElement('analyzeButton'),
            resetButton: getElement('resetButton'),
            copyJsonButton: getElement('copyJsonButton'),
            downloadJsonButton: getElement('downloadJsonButton'),
            resultSummary: getElement('resultSummary'),
            loadingIndicator: getElement('loadingIndicator'),
            resultSection: getElement('resultSection'),
            basicInfo: getMetadataContainer('basicInfo'),
            technicalInfo: getMetadataContainer('technicalInfo'),
            gpsInfo: getMetadataContainer('gpsInfo'),
            advancedInfo: getMetadataContainer('advancedInfo'),
            otherInfo: getMetadataContainer('otherInfo'),
            fileInfo: getMetadataContainer('fileInfo'),
            errorContainer: getElement('errorContainer')
        },

        config: {
            maxFileSize: 16 * 1024 * 1024,
            allowedTypes: acceptedTypes,
            allowedExtensions: acceptedExtensions,
            uploadEndpoint: '/upload',
            metadataCategories: [
                {
                    key: 'basic_info',
                    element: 'basicInfo',
                    description: 'General image details such as format, dimensions, and color mode.'
                },
                {
                    key: 'technical_info',
                    element: 'technicalInfo',
                    description: 'Technical properties such as resolution, aspect ratio, DPI, and channels.'
                },
                {
                    key: 'gps_info',
                    element: 'gpsInfo',
                    description: 'GPS coordinates and altitude when available.'
                },
                {
                    key: 'advanced_info',
                    element: 'advancedInfo',
                    description: 'Camera capture settings such as flash, metering, zoom, and white balance.'
                },
                {
                    key: 'other_info',
                    element: 'otherInfo',
                    description: 'Additional metadata that does not fit the main groups.'
                },
                {
                    key: 'file_info',
                    element: 'fileInfo',
                    description: 'File integrity and processing details.'
                }
            ]
        },

        init() {
            this.dragDepth = 0;
            this.lastMetadata = null;
            this.bindEvents();
            this.setupDragAndDrop();
        },

        bindEvents() {
            this.elements.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
            this.elements.analyzeButton.addEventListener('click', this.handleAnalyze.bind(this));
            this.elements.resetButton.addEventListener('click', this.resetSelectedFile.bind(this));
            this.elements.copyJsonButton.addEventListener('click', this.copyMetadata.bind(this));
            this.elements.downloadJsonButton.addEventListener('click', this.downloadMetadata.bind(this));
            this.elements.form.addEventListener('submit', this.handleAnalyze.bind(this));
            this.elements.dropZone.addEventListener('click', this.handleDropZoneClick.bind(this));
            this.elements.dropZone.addEventListener('keydown', this.handleDropZoneKeydown.bind(this));
        },

        setupDragAndDrop() {
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                this.elements.dropZone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                });
            });

            this.elements.dropZone.addEventListener('dragenter', () => {
                this.dragDepth += 1;
                this.elements.dropZone.classList.add('dragover');
            });

            this.elements.dropZone.addEventListener('dragleave', () => {
                this.dragDepth = Math.max(0, this.dragDepth - 1);
                if (this.dragDepth === 0) {
                    this.elements.dropZone.classList.remove('dragover');
                }
            });

            this.elements.dropZone.addEventListener('drop', this.handleDrop.bind(this));
        },

        handleDropZoneClick(event) {
            if (event.target === this.elements.fileInput || event.target.closest('label')) {
                return;
            }
            this.elements.fileInput.click();
        },

        handleDropZoneKeydown(event) {
            if (!getActionKey(event)) {
                return;
            }
            event.preventDefault();
            this.elements.fileInput.click();
        },

        handleFileSelect(event) {
            const file = event.target.files[0];
            if (file) {
                this.validateAndPreviewFile(file);
            } else {
                this.resetSelectedFile();
            }
        },

        handleDrop(event) {
            this.dragDepth = 0;
            const file = event.dataTransfer.files[0];
            if (file) {
                this.elements.fileInput.files = event.dataTransfer.files;
                this.validateAndPreviewFile(file);
            }
            this.elements.dropZone.classList.remove('dragover');
        },

        validateAndPreviewFile(file) {
            this.hideError();

            if (!this.isAllowedImage(file)) {
                this.resetSelectedFile();
                this.showError('Please choose a valid image file (JPG, PNG, GIF, TIFF, BMP, or WEBP).');
                return false;
            }
            
            if (file.size > this.config.maxFileSize) {
                this.resetSelectedFile();
                this.showError(`The file is too large. The maximum size is ${this.formatFileSize(this.config.maxFileSize)}.`);
                return false;
            }

            this.previewImage(file);
            return true;
        },

        isAllowedImage(file) {
            const extension = file.name.split('.').pop().toLowerCase();
            return (
                this.config.allowedTypes.has(file.type) ||
                this.config.allowedExtensions.has(extension)
            );
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
                this.elements.selectedFileSummary.replaceChildren(
                    this.createSummaryItem('File', file.name),
                    this.createSummaryItem('Type', file.type || 'Unknown'),
                    this.createSummaryItem('Size', this.formatFileSize(file.size))
                );
                this.elements.previewContainer.classList.remove('hidden');
                this.elements.dropZone.classList.add('hidden');
                this.elements.resultSection.classList.add('hidden');
                this.elements.analyzeButton.disabled = false;
            };
            reader.onerror = () => {
                this.resetSelectedFile();
                this.showError('Could not load the image preview.');
            };
            reader.readAsDataURL(file);
        },

        async handleAnalyze(event) {
            event.preventDefault();
            
            if (!this.elements.fileInput.files.length) {
                this.showError('Please choose an image first.');
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
                    throw new Error(data.error || `HTTP error: ${response.status}`);
                }
                
                this.displayMetadata(data);
                
            } catch (error) {
                this.showError(`Could not process the image: ${error.message}`);
                this.elements.resultSection.classList.add('hidden');
            } finally {
                this.setLoading(false);
            }
        },

        setLoading(isLoading) {
            this.elements.loadingIndicator.classList.toggle('hidden', !isLoading);
            this.elements.analyzeButton.disabled = isLoading;
            this.elements.dropZone.setAttribute('aria-busy', String(isLoading));
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

            this.lastMetadata = metadata;
            this.clearMetadata();

            this.config.metadataCategories.forEach(({ key, element, description }) => {
                this.renderMetadataCategory(key, metadata, this.elements[element], description);
            });

            this.updateResultSummary(metadata);
            this.elements.resultSection.classList.remove('hidden');
        },

        clearMetadata() {
            this.config.metadataCategories.forEach(({ element }) => {
                const container = this.elements[element];
                container.replaceChildren();
            });
        },

        renderMetadataCategory(category, metadata, container, description) {
            const data = metadata[category];
            if (data && Object.keys(data).length > 0) {
                const descriptionElement = document.createElement('p');
                descriptionElement.className = 'category-description';
                descriptionElement.textContent = description;
                container.appendChild(descriptionElement);
                this.renderMetadataSection(data, container);
            } else {
                const noData = document.createElement('p');
                noData.className = 'no-data';
                noData.textContent = `No ${category.replace(/_/g, ' ')} available.`;
                container.appendChild(noData);
            }
        },

        renderMetadataSection(data, container) {
            const fragment = document.createDocumentFragment();

            Object.entries(data).forEach(([key, value]) => {
                const item = document.createElement('div');
                item.className = 'metadata-item';

                const keyElement = document.createElement('span');
                keyElement.className = 'metadata-key';
                keyElement.textContent = this.formatKey(key);

                const valueElement = document.createElement('span');
                valueElement.className = 'metadata-value';
                const formattedValue = this.formatValue(value);
                valueElement.textContent = formattedValue;
                if (formattedValue.length > 32 || typeof value === 'object') {
                    valueElement.classList.add('is-long');
                }

                item.append(keyElement, valueElement);
                fragment.appendChild(item);
            });

            container.appendChild(fragment);
        },

        formatKey(key) {
            if (keyLabels[key]) {
                return keyLabels[key];
            }

            return key
                .replace(/([A-Z])/g, ' $1')
                .replace(/_/g, ' ')
                .trim()
                .replace(/\b\w/g, l => l.toUpperCase());
        },

        formatValue(value) {
            if (value === null || value === undefined) {
                return 'Not available';
            }
            if (typeof value === 'object') {
                return JSON.stringify(value, null, 2);
            }
            if (typeof value === 'number') {
                return numberFormatter.format(value);
            }
            return String(value);
        },

        createSummaryItem(label, value) {
            const item = document.createElement('span');
            item.className = 'summary-item';

            const labelElement = document.createElement('strong');
            labelElement.textContent = `${label}:`;

            const valueElement = document.createElement('span');
            valueElement.textContent = value;

            item.append(labelElement, valueElement);
            return item;
        },

        updateResultSummary(metadata) {
            const fileInfo = metadata.file_info || {};
            const bits = [];

            if (fileInfo.filename) {
                bits.push(fileInfo.filename);
            }
            if (fileInfo.size_human) {
                bits.push(fileInfo.size_human);
            }
            if (fileInfo.processed_at || fileInfo.timestamp) {
                const parsedDate = new Date(fileInfo.processed_at || fileInfo.timestamp);
                if (!Number.isNaN(parsedDate.getTime())) {
                    bits.push(`processed ${dateFormatter.format(parsedDate)}`);
                }
            }

            this.elements.resultSummary.textContent = bits.length
                ? bits.join(' · ')
                : 'Metadata extracted successfully';
        },

        getMetadataJson() {
            return JSON.stringify(this.lastMetadata, null, 2);
        },

        async copyMetadata() {
            if (!this.lastMetadata) {
                this.showError('There are no results to copy yet.');
                return;
            }

            try {
                await navigator.clipboard.writeText(this.getMetadataJson());
                this.setActionFeedback(this.elements.copyJsonButton, 'Copied');
            } catch (error) {
                this.showError('Could not copy the JSON. Try downloading it instead.');
            }
        },

        downloadMetadata() {
            if (!this.lastMetadata) {
                this.showError('There are no results to download yet.');
                return;
            }

            const fileInfo = this.lastMetadata.file_info || {};
            const baseName = (fileInfo.filename || 'metafinder-result')
                .replace(/\.[^/.]+$/, '')
                .replace(/[^a-z0-9_-]/gi, '-')
                .replace(/-+/g, '-')
                .replace(/^-|-$/g, '') || 'metafinder-result';
            const blob = new Blob([this.getMetadataJson()], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');

            link.href = url;
            link.download = `${baseName}-metadata.json`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            this.setActionFeedback(this.elements.downloadJsonButton, 'Downloaded');
        },

        setActionFeedback(button, label) {
            const original = button.textContent;
            button.textContent = label;
            button.disabled = true;

            window.setTimeout(() => {
                button.textContent = original;
                button.disabled = false;
            }, 1400);
        },

        showError(message) {
            this.elements.errorContainer.textContent = message;
            this.elements.errorContainer.classList.remove('hidden');
            const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            this.elements.errorContainer.scrollIntoView({
                behavior: prefersReducedMotion ? 'auto' : 'smooth',
                block: 'nearest'
            });
        },

        hideError() {
            this.elements.errorContainer.classList.add('hidden');
            this.elements.errorContainer.textContent = '';
        },

        resetSelectedFile() {
            this.lastMetadata = null;
            this.elements.fileInput.value = '';
            this.elements.imagePreview.removeAttribute('src');
            this.elements.selectedFileSummary.replaceChildren();
            this.elements.previewContainer.classList.add('hidden');
            this.elements.dropZone.classList.remove('hidden');
            this.elements.resultSection.classList.add('hidden');
            this.elements.analyzeButton.disabled = true;
            this.hideError();
        }
    };

    MetaFinder.init();
});
