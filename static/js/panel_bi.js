/**
 * Inicializa TODOS los gráficos del panel.
 */
function inicializarGraficosBI(dataTalleres, dataActas, dataParticipacion, dataDemografia, dataAsistencia,) {
    if(dataParticipacion) dibujarParticipacionGauge(dataParticipacion);
    if(dataDemografia) dibujarDemografiaSector(dataDemografia);
    if(dataTalleres) dibujarOcupacionTalleres(dataTalleres);
    if(dataActas) dibujarConsultaActas(dataActas);
    if(dataAsistencia) dibujarAsistenciaReuniones(dataAsistencia);
}

// Paleta de colores
const COLORES = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69', '#fd7e14', '#20c9a6', '#6610f2'];

// 1. Participación (Gauge) - Verde y Gris
function dibujarParticipacionGauge(data) {
    const ctx = document.getElementById('graficoParticipacionGauge');
    if (!ctx) return;
    const porcentaje = data.porcentaje_actual;
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Participación', 'Faltante'],
            datasets: [{ 
                data: [porcentaje, 100 - porcentaje], 
                backgroundColor: ['#1cc88a', '#eaecf4'], 
                borderWidth: 0, circumference: 180, rotation: 270 
            }]
        },
        options: { responsive: true, cutout: '80%', plugins: { legend: { display: false }, title: { display: true, text: `${porcentaje.toFixed(1)}%` } } }
    });
}

// 2. Demografía (Torta) - Multicolor
function dibujarDemografiaSector(data) {
    const ctx = document.getElementById('graficoDemografiaSector');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'pie',
        data: { 
            labels: data.map(d => d.direccion_sector || 'S/N'), 
            datasets: [{ 
                data: data.map(d => d.total_vecinos), 
                backgroundColor: COLORES 
            }] 
        },
        options: { plugins: { legend: { position: 'right' } } }
    });
}

// 3. Talleres (Barras) - Azul y Gris
function dibujarOcupacionTalleres(data) {
    const ctx = document.getElementById('graficoOcupacionTalleres');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'bar',
        data: { 
            labels: data.map(d => d.nombre), 
            datasets: [
                { label: 'Inscritos', data: data.map(d => d.inscritos), backgroundColor: '#4e73df' },
                { label: 'Cupos', data: data.map(d => d.cupos), backgroundColor: '#eaecf4' }
            ] 
        },
        options: { scales: { x: { stacked: false }, y: { beginAtZero: true } } }
    });
}

// 4. Actas (Barras Horiz.) - Cian
function dibujarConsultaActas(data) {
    const ctx = document.getElementById('graficoConsultaActas');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'bar',
        data: { 
            labels: data.map(d => d.acta__titulo), 
            datasets: [{ label: 'Consultas', data: data.map(d => d.consultas), backgroundColor: '#36b9cc' }] 
        },
        options: { indexAxis: 'y' }
    });
}

// 5. Asistencia (Línea) - Amarillo
function dibujarAsistenciaReuniones(data) {
    const ctx = document.getElementById('graficoAsistencia');
    if (!ctx) return;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.fecha),
            datasets: [{
                label: 'Asistentes',
                data: data.map(d => d.total),
                borderColor: '#f6c23e',
                backgroundColor: 'rgba(246, 194, 62, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: { responsive: true }
    });
}

