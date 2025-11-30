// Asegúrese de que la librería Chart.js esté cargada antes de este script.

/**
 * Función principal llamada desde el HTML para inicializar todos los gráficos del panel BI.
 */
function inicializarGraficosBI(dataTalleres, dataActas, dataParticipacion, dataDemografia) {
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
    
    // 4. Gráfico de Tasa de Consulta de Actas (Top 10) - CORRECCIÓN
    if (dataActas && dataActas.length > 0) {
        dibujarConsultaActas(dataActas); 
    }

    // Nota: El quinto argumento (dataTendenciaActas) se eliminó de la vista 
    // y la lógica asociada (dibujarTendenciaActas) se reemplazó/eliminó, 
    // ya que no se usaba correctamente en el panel actual.
}

// =========================================================
// 4. GRÁFICO DE TASA DE CONSULTA DE ACTAS (TOP 10) - CORRECCIÓN
// =========================================================
function dibujarConsultaActas(data) {
    const ctx = document.getElementById('graficoConsultaActas');
    if (!ctx) return; 

    const labels = data.map(item => item.acta__titulo);
    const consultas = data.map(item => item.consultas);

    new Chart(ctx, {
        type: 'bar', // Gráfico de barras horizontal para Top 10
        data: {
            labels: labels,
            datasets: [{
                label: 'Número de Consultas',
                data: consultas,
                backgroundColor: 'rgba(255, 99, 132, 0.8)', // Color de Actas
                borderColor: 'rgb(255, 99, 132)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Hace la barra horizontal
            plugins: {
                legend: { display: false },
                title: { 
                    display: true,
                    text: 'Actas Más Consultadas (Top 10)'
                },
                tooltip: {
                    callbacks: {
                        label: (context) => ` ${context.parsed.x} consultas`
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: 'Cantidad de Consultas' },
                    ticks: { stepSize: 1 } // Solo enteros
                },
                y: {
                    // Configuración por defecto
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