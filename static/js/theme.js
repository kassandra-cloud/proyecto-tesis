/* static/js/theme.js */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Encontrar el interruptor (checkbox)
    const toggleButton = document.getElementById('dark-mode-toggle');
    // El elemento <html> controla el tema de Bootstrap
    const htmlElement = document.documentElement; 

    // 2. Función para aplicar el tema
    function aplicarTema(tema) {
        if (tema === 'dark') {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            if(toggleButton) toggleButton.checked = true;
        } else {
            htmlElement.setAttribute('data-bs-theme', 'light');
            if(toggleButton) toggleButton.checked = false;
        }
    }

    // 3. Cargar la preferencia guardada del usuario
    const temaGuardado = localStorage.getItem('theme');
    const temaActual = temaGuardado || htmlElement.getAttribute('data-bs-theme');

    aplicarTema(temaActual);

    // 4. Evento al hacer click en el interruptor
    if (toggleButton) {
        toggleButton.addEventListener('click', () => {
            let nuevoTema;
            if (toggleButton.checked) {
                nuevoTema = 'dark';
            } else {
                nuevoTema = 'light';
            }
            // Guardar la preferencia en localStorage
            localStorage.setItem('theme', nuevoTema);
            // Aplicar el tema visualmente
            aplicarTema(nuevoTema);
        });
    }
});