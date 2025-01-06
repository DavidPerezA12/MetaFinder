# MetaFinder

Aplicación web para extraer y visualizar metadatos EXIF de imágenes, con interfaz glass-morphism y procesamiento seguro de archivos.

## Características

- Subida de imágenes por drag & drop
- Visualización de metadatos en categorías:
  - Información básica
  - Información técnica
  - Datos GPS
  - Otros detalles
- Soporte para múltiples formatos (JPG, PNG, GIF, TIFF, BMP)
- Límite de tamaño: 16MB
- Diseño responsive

## Requisitos

- Python 3.6+
- pip

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/DavidPerezA12/MetaFinder.git
cd MetaFinder
```

2. Crear y activar entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Estructura del Proyecto

```
MetaFinder/
├── frontend/
│   ├── html/
│   │   └── index.html
│   └── static/
│       ├── css/
│       ├── js/
│       └── img/
├── scripts/
│   └── processor.py
├── uploads/
├── app.py
└── requirements.txt
```

## Uso

1. Iniciar servidor:
```bash
python app.py
```

2. Abrir en navegador:
```
http://localhost:5000
```

## Características Técnicas

### Backend
- Flask con CORS habilitado
- Validación de tipos mediante python-magic
- Procesamiento de metadatos con piexif
- Manejo seguro de archivos temporales
- Generación de hash para integridad

### Frontend
- Diseño glass-morphism moderno
- JavaScript vanilla para manipulación del DOM
- Previsualización de imágenes en tiempo real
- Interfaz responsive

## API

### POST /upload
- Acepta: Imagen (multipart/form-data)
- Retorna: JSON con metadatos categorizados
- Validaciones:
  - Tipo de archivo
  - Tamaño máximo
  - Integridad

## Licencia

Proyecto bajo la Licencia MIT

## Contacto

David Pérez - [@DavidPerezA12](https://github.com/DavidPerezA12)

Repositorio: [https://github.com/DavidPerezA12/MetaFinder]