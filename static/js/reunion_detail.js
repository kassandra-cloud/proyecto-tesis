/* static/js/reunion_detail.js */

document.addEventListener('DOMContentLoaded', () => {

    // ===============================
    // Configuración global
    // ===============================
    const config = window.REUNION_CONFIG || {};

    function getCSRF() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // =====================================================
    // 1. TRANSCRIPCIÓN STT + GRABACIÓN + AUTOGUARDADO
    // =====================================================
    const btnStart = document.getElementById('btnStartSTT');
    const btnStop = document.getElementById('btnStopSTT');
    const sttStatus = document.getElementById('sttStatus');
    const actaTextarea = document.getElementById('actaContenido');
    const autosaveStatus = document.getElementById('autosave-status');

    const audioPreviewContainer = document.getElementById('audioPreviewContainer');
    const audioPlayer = document.getElementById('audioPlayer');
    const downloadAudioLink = document.getElementById('downloadAudioLink');
    const audioFileName = document.getElementById('audioFileName');

    if (btnStart && actaTextarea) {

        let autosaveTimer = null;
        const AUTOSAVE_DELAY = 2500;

        async function guardarBorrador() {
            if (!autosaveStatus) return;

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
                    autosaveStatus.textContent = 'Borrador guardado';
                    autosaveStatus.classList.add('text-success');
                } else {
                    autosaveStatus.textContent = 'Error al guardar';
                    autosaveStatus.classList.add('text-danger');
                }
            } catch (e) {
                autosaveStatus.textContent = 'Error de red';
                autosaveStatus.classList.add('text-danger');
            }
        }

        function triggerAutosave() {
            clearTimeout(autosaveTimer);
            autosaveTimer = setTimeout(guardarBorrador, AUTOSAVE_DELAY);
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            btnStart.disabled = true;
            if (sttStatus) sttStatus.textContent = 'Transcripción no soportada en este navegador';
            return;
        }

        let micStream = null;
        let mediaRecorder = null;
        let audioChunks = [];
        let isRecording = false;

        const recognition = new SpeechRecognition();
        recognition.lang = 'es-ES';
        recognition.continuous = true;
        recognition.interimResults = true;

        let finalTranscript = actaTextarea.value || '';

        recognition.onstart = () => {
            sttStatus.textContent = '🎙️ Escuchando...';
            btnStart.disabled = true;
            btnStop.disabled = false;
        };

        recognition.onend = () => {
            if (isRecording) {
                recognition.start();
                return;
            }
            sttStatus.textContent = 'Micrófono inactivo';
            btnStart.disabled = false;
            btnStop.disabled = true;
            triggerAutosave();
        };

        recognition.onresult = (event) => {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + '. ';
                } else {
                    interim += event.results[i][0].transcript;
                }
            }
            actaTextarea.value = finalTranscript + interim;
            actaTextarea.scrollTop = actaTextarea.scrollHeight;
            triggerAutosave();
        };

        btnStart.addEventListener('click', async () => {
            try {
                micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

                audioChunks = [];
                mediaRecorder = new MediaRecorder(micStream);
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

                mediaRecorder.onstop = () => {
                    const blob = new Blob(audioChunks, { type: 'audio/webm' });
                    const url = URL.createObjectURL(blob);

                    audioPlayer.src = url;

                    let titulo = (config.reunionTitulo || `reunion-${config.reunionId}`)
                        .replace(/\s+/g, '_')
                        .replace(/[^a-zA-Z0-9_-]/g, '')
                        .toLowerCase();

                    const fecha = config.reunionFecha || new Date().toISOString().split('T')[0];
                    const nombre = `${titulo}_${fecha}.webm`;

                    downloadAudioLink.href = url;
                    downloadAudioLink.download = nombre;
                    audioFileName.textContent = nombre;

                    audioPreviewContainer.style.display = 'block';
                };

                mediaRecorder.start();
                isRecording = true;
                finalTranscript = actaTextarea.value + ' ';
                recognition.start();

            } catch (err) {
                sttStatus.textContent = 'No se pudo acceder al micrófono';
            }
        });

        btnStop.addEventListener('click', () => {
            isRecording = false;
            recognition.stop();
            if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
            micStream?.getTracks().forEach(t => t.stop());
        });
    }

    // =====================================================
    // 2. ENVÍO DE ACTA POR CORREO
    // =====================================================
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

        const setMsg = (msg, ok = false) => {
            btnSubmit.disabled = false;
            btnTexto.style.display = 'inline';
            btnSpinner.style.display = 'none';
            msgErr.style.display = 'none';
            msgOk.style.display = 'none';

            if (!msg) return;
            (ok ? msgOk : msgErr).textContent = msg;
            (ok ? msgOk : msgErr).style.display = 'block';
        };

        chkAll?.addEventListener('change', e => {
            lista.querySelectorAll('.chk-email').forEach(cb => cb.checked = e.target.checked);
        });

        formEmail.addEventListener('submit', async e => {
            e.preventDefault();

            btnSubmit.disabled = true;
            btnTexto.style.display = 'none';
            btnSpinner.style.display = 'inline';

            const seleccionados = Array.from(lista.querySelectorAll('.chk-email:checked')).map(c => c.value);
            const extras = txtAdicionales.value.split(',').map(e => e.trim()).filter(Boolean);
            const correos = [...new Set([...seleccionados, ...extras])];

            if (!correos.length) {
                setMsg('Selecciona al menos un correo');
                return;
            }

            const fd = new FormData();
            correos.forEach(c => fd.append('correos[]', c));

            try {
                const resp = await fetch(config.urls.enviarCorreo, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCSRF() },
                    body: fd
                });

                const data = await resp.json();
                if (resp.ok && data.ok) {
                    setMsg('Acta enviada correctamente', true);
                } else {
                    setMsg(data.message || 'Error al enviar');
                }
            } catch {
                setMsg('Error de red');
            }
        });
    }

    // =====================================================
    // 3. POLLING ESTADO DE TRANSCRIPCIÓN
    // =====================================================
    const barra = document.getElementById('transcripcion-pendiente');
    if (barra && config.urls.estadoActa) {
        const poll = setInterval(async () => {
            try {
                const r = await fetch(config.urls.estadoActa);
                const d = await r.json();
                if (['COMPLETADO', 'ERROR'].includes(d.estado)) {
                    clearInterval(poll);
                    location.reload();
                }
            } catch {
                clearInterval(poll);
            }
        }, 5000);
    }

});
