/* static/js/reunion_detail.js */

document.addEventListener('DOMContentLoaded', () => {
    // Obtenemos la configuración desde el HTML
    const config = window.REUNION_CONFIG || {};
    
    // Helper para CSRF
    function getCSRF() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // --- 1. Lógica de Transcripción (STT), GRABACIÓN y AUTOGUARDADO ---
    const btnStart = document.getElementById('btnStartSTT');
    const btnStop = document.getElementById('btnStopSTT');
    const sttStatus = document.getElementById('sttStatus');
    const actaTextarea = document.getElementById('actaContenido');
    const autosaveStatus = document.getElementById('autosave-status');
    
    const audioPreviewContainer = document.getElementById('audioPreviewContainer');
    const audioPlayer = document.getElementById('audioPlayer');
    const downloadAudioLink = document.getElementById('downloadAudioLink');
    const audioFileName = document.getElementById('audioFileName');

    if (btnStart) {
        // Autoguardado
        let autosaveTimer = null;
        const AUTOSAVE_DELAY = 2500; 

        async function guardarBorrador() {
            if (!actaTextarea || !autosaveStatus) return;
            autosaveStatus.textContent = 'Guardando...';
            autosaveStatus.className = 'text-muted small me-2';

            const formData = new FormData();
            formData.append('contenido', actaTextarea.value);

            try {
                const response = await fetch(config.urls.guardarBorrador, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRF(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: formData
                });

                if (response.ok) {
                    autosaveStatus.textContent = 'Borrador guardado.';
                    autosaveStatus.classList.add('text-success');
                } else {
                    autosaveStatus.textContent = 'Error al guardar.';
                    autosaveStatus.classList.add('text-danger');
                }
            } catch (error) {
                console.error('Error en autoguardado:', error);
                autosaveStatus.textContent = 'Error de red.';
                autosaveStatus.classList.add('text-danger');
            }
        }

        function triggerAutosave() {
            if (autosaveTimer) clearTimeout(autosaveTimer);
            autosaveTimer = setTimeout(guardarBorrador, AUTOSAVE_DELAY);
        }

        // Speech API
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            btnStart.disabled = true;
            if(sttStatus) sttStatus.textContent = "Transcripción no soportada en este navegador.";
            return;
        }

        let micStream = null;
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;
        let recognition = new SpeechRecognition();
        
        recognition.lang = 'es-ES';
        recognition.continuous = true;
        recognition.interimResults = true; 
        
        let finalTranscript = actaTextarea ? actaTextarea.value : '';

        recognition.onstart = () => {
            sttStatus.textContent = '🎙️ Escuchando...';
            btnStart.disabled = true;
            btnStop.disabled = false;
        };

        recognition.onend = () => {
            if (isRecording) {
                recognition.start(); // Reiniciar si se cortó solo
                return;
            }
            sttStatus.textContent = 'Micrófono inactivo';
            btnStart.disabled = false;
            btnStop.disabled = true;
            triggerAutosave();
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + '. ';
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }
            if (actaTextarea) {
                actaTextarea.value = finalTranscript + interimTranscript;
                actaTextarea.scrollTop = actaTextarea.scrollHeight;
                triggerAutosave();
            }
        };

        // Botón Iniciar
        btnStart.addEventListener('click', async () => {
            if (audioPlayer.src) {
                URL.revokeObjectURL(audioPlayer.src);
                audioPlayer.src = null;
            }
            if(audioPreviewContainer) audioPreviewContainer.style.display = 'none';

            try {
                micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = [];
                mediaRecorder = new MediaRecorder(micStream);
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    if(audioPlayer) audioPlayer.src = audioUrl;
                    
                    // --- INICIO DE LA MEJORA ---
                    
                    // 1. Obtenemos el título y la fecha desde la configuración
                    let tituloSeguro = config.reunionTitulo || `reunion-${config.reunionId}`;
                    const fechaSegura = config.reunionFecha || new Date().toISOString().split('T')[0];

                    // 2. Limpiamos el título para que sea un nombre de archivo válido
                    // Reemplazamos espacios por guiones bajos y quitamos caracteres especiales
                    tituloSeguro = tituloSeguro
                        .replace(/\s+/g, '_')           // Espacios a guiones bajos
                        .replace(/[^a-zA-Z0-9_\-]/g, '') // Eliminar caracteres no alfanuméricos (opcional, por seguridad)
                        .toLowerCase();

                    // 3. Generamos el nombre final: ej. "reunion_ordinaria_2025-11-26.webm"
                    const nombreArchivo = `${tituloSeguro}_${fechaSegura}.webm`;

                    // --- FIN DE LA MEJORA ---

                    if(downloadAudioLink) {
                        downloadAudioLink.href = audioUrl;
                        downloadAudioLink.download = nombreArchivo;
                    }
                    if(audioFileName) audioFileName.textContent = nombreArchivo;
                    if(audioPreviewContainer) audioPreviewContainer.style.display = 'block';
                    audioChunks = [];
                };
                
                mediaRecorder.start();
                isRecording = true;
                if (actaTextarea) finalTranscript = actaTextarea.value + ' ';
                recognition.start(); 

            } catch (err) {
                console.error(err);
                sttStatus.textContent = "Error: No se pudo acceder al micrófono.";
            }
        });

        // Botón Detener
        btnStop.addEventListener('click', () => {
            isRecording = false;
            if (recognition) recognition.stop();
            if (mediaRecorder && mediaRecorder.state === "recording") mediaRecorder.stop();
            if (micStream) {
                micStream.getTracks().forEach(track => track.stop());
                micStream = null;
            }
        });
    }

    // --- 2. Lógica de Envío de Email ---
    const formEmail = document.getElementById('formEnviarEmail');
    if (formEmail) {
        const btnSubmit = document.getElementById('btnEnviarCorreo');
        const btnTexto = document.getElementById('btnEnviarTexto');
        const btnSpinner = document.getElementById('btnEnviarSpinner');
        const chkAll = document.getElementById('chkTodosVecinos');
        const lista = document.getElementById('lista-correos-vecinos');
        const txtAdicionales = document.getElementById('correos_adicionales');
        const msgErr = document.getElementById('email-error-msg');
        const msgOk = document.getElementById('email-success-msg');

        const setSend = (msg, isSuccess = false) => {
            btnTexto.style.display = 'inline';
            btnSpinner.style.display = 'none';
            btnSubmit.disabled = false;
            msgErr.style.display = 'none';
            msgOk.style.display = 'none';
            if (!msg) return;
            const target = isSuccess ? msgOk : msgErr;
            target.textContent = msg;
            target.style.display = 'block';
        }

        if(chkAll && lista) {
            chkAll.addEventListener('change', (e) => {
                lista.querySelectorAll('.chk-email').forEach(cb => cb.checked = e.target.checked);
            });
        }

        formEmail.addEventListener('submit', async (e) => {
            e.preventDefault();
            btnSubmit.disabled = true;
            btnTexto.style.display = 'none';
            btnSpinner.style.display = 'inline';
            
            let marcados = [];
            if (lista) marcados = Array.from(lista.querySelectorAll('.chk-email:checked')).map(cb => cb.value);
            
            let extras = [];
            if (txtAdicionales) extras = txtAdicionales.value.split(',').map(e => e.trim()).filter(Boolean);

            const todos = [...new Set([...marcados, ...extras])];
            if (!todos.length){
                setSend('Selecciona al menos un correo.', false);
                return;
            }

            const fd = new FormData();
            todos.forEach(c => fd.append('correos[]', c));

            try {
                const resp = await fetch(config.urls.enviarCorreo, {
                    method:'POST',
                    headers:{'X-CSRFToken': getCSRF()},
                    body: fd
                });
                
                const data = await resp.json(); // Asumimos JSON incluso en error si el backend está bien
                if (resp.ok && data.ok){
                    setSend('¡Acta enviada correctamente!', true);
                    setTimeout(()=> {
                        // Cerrar modal usando Bootstrap global
                        const modalEl = document.getElementById('modalEnviarActa');
                        if (modalEl && window.bootstrap){
                            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                            modal.hide();
                        }
                        setSend('');
                        formEmail.reset();
                    }, 1500);
                } else {
                    setSend(data.message || 'Error al enviar', false);
                }
            } catch(err) {
                setSend('Error de red.', false);
            }
        });
    }

    // --- 3. Polling de Estado de Transcripción (Vosk) ---
    const barraEstado = document.getElementById('transcripcion-pendiente');
    if (barraEstado && config.urls.estadoActa) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(config.urls.estadoActa);
                if (!response.ok) return;
                const data = await response.json();
                
                if (data.estado === 'COMPLETADO' || data.estado === 'ERROR') {
                    clearInterval(pollInterval);
                    window.location.reload();
                }
            } catch (error) {
                clearInterval(pollInterval);
            }
        }, 5000);
    }
});