/* static/js/foro_lista.js */

// 1. Configuración HTMX (si se usa)
document.addEventListener("htmx:configRequest", (e) => {
    const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (token) e.detail.headers['X-CSRFToken'] = token;
});

// 2. Toggle para formularios de respuesta
document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-reply]');
    if (!btn) return;
    e.preventDefault();
    const id = btn.getAttribute('data-reply');
    const form = document.getElementById('reply-form-' + id);
    if (form) form.style.display = (form.style.display === 'none' || !form.style.display) ? 'block' : 'none';
});

// 3. Lógica de Grabación de Audio (Nuevo Post)
document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-record');
    const stopBtn = document.getElementById('stop-record');
    const audioPlayback = document.getElementById('audio-playback');
    const fileInput = document.getElementById('id_archivos');

    if (!startBtn || !fileInput) return;

    let mediaRecorder;
    let audioChunks = [];

    startBtn.addEventListener('click', async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = () => {
                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const url = URL.createObjectURL(blob);
                if(audioPlayback) {
                    audioPlayback.src = url;
                    audioPlayback.style.display = 'block';
                }
                
                // Inyectar archivo en el input
                const file = new File([blob], 'grabacion_foro.webm', { type: 'audio/webm' });
                const dt = new DataTransfer();
                // Mantenemos archivos previos si los hubiera
                for (let i = 0; i < fileInput.files.length; i++) dt.items.add(fileInput.files[i]);
                dt.items.add(file);
                fileInput.files = dt.files;
                
                audioChunks = [];
            };
            mediaRecorder.start();
            startBtn.disabled = true;
            stopBtn.disabled = false;
            if(audioPlayback) audioPlayback.style.display = 'none';
        } catch (err) {
            console.error('Error micrófono:', err);
            alert('No se pudo acceder al micrófono.');
        }
    });

    stopBtn.addEventListener('click', () => {
        if (mediaRecorder) {
            mediaRecorder.stop();
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    });
});