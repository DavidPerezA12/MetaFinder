# MetaFinder

MetaFinder es una aplicación web que permite extraer y visualizar los metadatos EXIF de imágenes de manera sencilla y eficiente.

## Características

- Interfaz web intuitiva para subir imágenes
- Extracción de metadatos EXIF completos
- Visualización de datos en formato JSON
- Soporte para múltiples formatos de imagen
- Backend desarrollado en Flask
- Frontend responsive y moderno

## Requisitos Previos

- Python 3.x
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/DavidPerezA12/MetaFinder.git
cd MetaFinder
```

2. Crear y activar un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar las dependencias del backend:
```bash
pip install -r requirements.txt
```

4. Crear el directorio para uploads:
```bash
mkdir backend/uploads
```

## Uso

1. Iniciar el servidor Flask:
```bash
cd backend
python app.py
```

2. Abrir un navegador web y visitar:
```
http://localhost:5000
```

3. Seleccionar una imagen usando el botón de subida o arrastrando el archivo
4. Los metadatos se mostrarán automáticamente después de la subida

## Estructura del Proyecto

```
MetaFinder/
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── uploads/
│
├── frontend/
│   ├── css/
│   │   └── styles.css
│   ├── html/
│   │   └── index.html
│   └── js/
│       └── app.js
│
└── README.md
```

## Tecnologías Utilizadas

- **Backend**:
  - Flask (Framework web)
  - Pillow (Procesamiento de imágenes)
  - piexif (Extracción de metadatos EXIF)

- **Frontend**:
  - HTML5
  - CSS3
  - JavaScript (Vanilla)

## Contribución

Las contribuciones son bienvenidas. Por favor, sigue estos pasos:

1. Fork el proyecto
2. Crea una nueva rama (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contacto

David Pérez - [@DavidPerezA12](https://github.com/DavidPerezA12)

Link del Proyecto: [https://github.com/DavidPerezA12/MetaFinder]
