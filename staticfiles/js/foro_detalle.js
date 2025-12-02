// static/js/foro_detalle.js

// ===================================================================
// Lógica para Mostrar/Ocultar Formularios de Respuesta (EXISTENTE)
// Esta lógica controla la visibilidad de los formularios creados dinámicamente en HTML
// ===================================================================

document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-reply]');
    if (!btn) return;
    e.preventDefault();
    const id = btn.getAttribute('data-reply');
    const form = document.getElementById('reply-form-' + id);
    if (form) {
        form.style.display = (form.style.display === 'none' || !form.style.display) ? 'block' : 'none';
    }
});

// ===================================================================
// Lógica para Grabación de Audio (NUEVO)
// Maneja la captura del micrófono, creación del archivo y asignación al input de Django
// ===================================================================

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-record-btn');
    const stopBtn = document.getElementById('stop-record-btn');
    const statusSpan = document.getElementById('recording-status');
    const playbackContainer = document.getElementById('audio-playback-container');
    const playbackAudio = document.getElementById('recorded-audio-playback');
    
    // Obtener el campo de subida de archivos de Django (el mismo que usa el formulario principal)
    const fileInput = document.querySelector('#collapseAdjunto input[type="file"]'); 

    if (!startBtn || !fileInput) return; // Salir si los elementos necesarios no están

    let mediaRecorder;
    let audioStream;
    let audioChunks = [];
    let recordedAudioFile = null; // Para guardar la referencia del archivo grabado

    // Función para limpiar y resetear la UI y el input de archivo
    const resetRecorder = () => {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusSpan.style.display = 'none';
        playbackContainer.style.display = 'none';
        audioChunks = [];
        recordedAudioFile = null;
        // Limpiar el input file
        fileInput.files = new DataTransfer().files; 
    };
    
    // Inicializar al cargar
    resetRecorder();

    startBtn.addEventListener('click', async () => {
        try {
            // 1. Pedir permiso y obtener el flujo de audio
            audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(audioStream);

            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                // 3. Crear el Blob y el objeto File (usando formato webm por compatibilidad)
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' }); 
                recordedAudioFile = new File([audioBlob], `grabacion-${Date.now()}.webm`, { type: 'audio/webm' });

                // 4. Asignar el archivo al input de Django
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(recordedAudioFile);
                fileInput.files = dataTransfer.files;
                
                // 5. Mostrar la previsualización del audio
                const audioUrl = URL.createObjectURL(audioBlob);
                playbackAudio.src = audioUrl;
                playbackContainer.style.display = 'block';

                // Liberar el micrófono
                audioStream.getTracks().forEach(track => track.stop());
            };

            // 2. Iniciar la grabación
            mediaRecorder.start();
            
            // Actualizar UI
            startBtn.disabled = true;
            stopBtn.disabled = false;
            statusSpan.style.display = 'inline';
            playbackContainer.style.display = 'none';
            
            // Asegurarse de limpiar el input por si había un archivo anterior
            fileInput.files = new DataTransfer().files;

        } catch (error) {
            console.error('Error al acceder al micrófono:', error);
            alert('No se pudo acceder al micrófono. Asegúrate de tener permisos y de usar HTTPS.');
            resetRecorder();
        }
    });

    stopBtn.addEventListener('click', () => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusSpan.style.display = 'none';
    });
    
    // Lógica para limpiar la grabación si el usuario sube un archivo normal
    fileInput.addEventListener('change', (e) => {
        // Verifica si el archivo que se está cargando es diferente del archivo grabado.
        // Esto previene que se borre la grabación justo después de ser asignada al input.
        if (e.target.files.length > 0 && e.target.files[0] !== recordedAudioFile) {
            resetRecorder();
        }
    });
});