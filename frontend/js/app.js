// app.js
document.getElementById('uploadForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    const formData = new FormData();
    const imageInput = document.getElementById('imageInput');
    formData.append('image', imageInput.files[0]);

    const response = await fetch('/upload', {
        method: 'POST',
        body: formData
    });

    const metadata = await response.json();
    document.getElementById('metadata').innerText = JSON.stringify(metadata, null, 2);
});

console.log("MetaFinder frontend loaded successfully.");