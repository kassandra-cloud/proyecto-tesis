// Asegúrese de que la librería Chart.js esté cargada antes de este script.

/**
 * Función principal llamada desde el HTML para inicializar todos los gráficos del panel BI.
 */
function inicializarGraficosBI(dataTalleres, dataActas, dataParticipacion, dataDemografia, dataTendenciaActas) {
    // 1. Gráfico Gauge de Participación
    if (dataParticipacion && Object.keys(dataParticipacion).length > 0) {
        dibujarParticipacionGauge(dataParticipacion);
    }
    
    // 2. Gráfico de Distribución Demográfica
    if (dataDemografia && dataDemografia.length > 0) {
        dibujarDemografiaSector(dataDemografia);
    }

    // 3. Gráfico de Ocupación de Talleres
    if (dataTalleres && dataTalleres.length > 0) {
        dibujarOcupacionTalleres(dataTalleres);
    }

    // 4. Gráfico de Tendencia de Consulta de Actas (Línea de Tiempo) [NUEVO]
    if (dataTendenciaActas && dataTendenciaActas.length > 0) {
        dibujarTendenciaActas(dataTendenciaActas); 
    }
}

// =========================================================
// 🆕 4. GRÁFICO DE TENDENCIA DE CONSULTA DE ACTAS (LÍNEA)
// =========================================================
function dibujarTendenciaActas(data) {
    const ctx = document.getElementById('graficoTendenciaActas');
    if (!ctx) return; 
    
    // 1. Procesar etiquetas (Meses)
    const labels = data.map(item => {
        // Agregamos 'T00:00:00' para asegurar que JS interprete la fecha en el día correcto
        const date = new Date(item.mes + 'T00:00:00'); 
        return date.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
    });
    
    // 2. Procesar valores
    const valores = data.map(item => item.total);

    // 3. Crear Gráfico de Línea
    new Chart(ctx, {
        type: 'line', 
        data: {
            labels: labels,
            datasets: [{
                label: 'Consultas Mensuales',
                data: valores,
                borderColor: '#287BFF',       // Azul Institucional
                backgroundColor: 'rgba(40, 123, 255, 0.1)', // Relleno suave
                borderWidth: 3,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#287BFF',
                pointRadius: 6,
                pointHoverRadius: 8,
                fill: true,   // Rellenar área bajo la curva
                tension: 0.4  // Curvatura suave
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { 
                    display: true,
                    text: 'Evolución de Consultas (Últimos 6 Meses)'
                },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ${context.parsed.y} consultas`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Cantidad' },
                    ticks: { stepSize: 1 }, // Solo enteros
                    grid: { borderDash: [2, 4] }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

// =========================================================
// 1. GRÁFICO GAUGE DE PARTICIPACIÓN
// =========================================================
function dibujarParticipacionGauge(data) {
    const ctx = document.getElementById('graficoParticipacionGauge');
    if (!ctx) return; 
    
    const porcentaje = data.porcentaje_actual;
    const restante = 100 - porcentaje;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Participación Actual', 'Restante'],
            datasets: [{
                data: [porcentaje, restante],
                backgroundColor: ['#287BFF', '#EEEEEE'], 
                borderWidth: 0,
                circumference: 180, 
                rotation: 270      
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '80%', 
            plugins: {
                legend: { display: false },
                title: { display: true, text: `Vecinos que participan: ${data.total_participantes} de ${data.total_vecinos}` },
                tooltip: { callbacks: { label: (context) => `${context.label}: ${context.parsed}%` } }
            }
        },
        plugins: [{
            id: 'textCenter',
            beforeDraw: function(chart) {
                const width = chart.width;
                const height = chart.height;
                const ctx = chart.ctx;
                ctx.restore();
                const fontSize = (height / 150).toFixed(2);
                ctx.font = fontSize + "em sans-serif";
                ctx.textBaseline = "middle";

                const text = porcentaje.toFixed(1) + "%";
                const textX = Math.round((width - ctx.measureText(text).width) / 2);
                const textY = height / 1.15; 

                ctx.fillStyle = '#1E1E28';
                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}

// =========================================================
// 2. GRÁFICO DE DISTRIBUCIÓN DEMOGRÁFICA
// =========================================================
function dibujarDemografiaSector(data) {
    const ctx = document.getElementById('graficoDemografiaSector');
    if (!ctx) return; 
    
    const labels = data.map(item => item.direccion_sector);
    const conteos = data.map(item => item.total_vecinos);
    const backgroundColors = [
        '#287BFF', '#5C9FF7', '#8EBDF0', '#C1DAE9', '#E7F2FF', '#D3E0EA', '#9FB7C7', '#6C8EA3'
    ];

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: conteos,
                backgroundColor: backgroundColors.slice(0, conteos.length),
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' },
                title: { display: true, text: 'Distribución por Sector' }
            }
        }
    });
}

// =========================================================
// 3. GRÁFICO DE OCUPACIÓN DE TALLERES
// =========================================================
function dibujarOcupacionTalleres(data) {
    const ctx = document.getElementById('graficoOcupacionTalleres');
    if (!ctx) return; 
    
    const labels = data.map(item => item.nombre);
    const inscritos = data.map(item => item.inscritos);
    const cupos = data.map(item => item.cupos);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Cupos Totales',
                    data: cupos,
                    backgroundColor: 'rgba(173, 216, 230, 0.7)',
                    borderColor: 'rgb(173, 216, 230)',
                    borderWidth: 1
                },
                {
                    label: 'Inscritos',
                    data: inscritos,
                    backgroundColor: 'rgba(40, 123, 255, 0.8)',
                    borderColor: 'rgb(40, 123, 255)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', 
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: 'Cantidad' }
                }
            }
        }
    });
}