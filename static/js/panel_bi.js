// Asegúrese de que la librería Chart.js esté cargada antes de este script.

/**
 * Función principal llamada desde el HTML para inicializar todos los gráficos del panel BI.
 * * @param {Array<Object>} dataTalleres - Datos de ocupación de talleres.
 * @param {Array<Object>} dataActas - Datos de consultas de actas (Top 10) - Se mantiene por si se necesita.
 * @param {Object} dataParticipacion - Datos de participación general (Gauge).
 * @param {Array<Object>} dataDemografia - Datos de distribución de vecinos por sector.
 * @param {Array<Object>} dataTendenciaActas - Datos de tendencia de consultas por mes (NUEVO).
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

    // 4. Gráfico de Consulta de Actas (Top 10) - YA NO SE LLAMA, HA SIDO REEMPLAZADO POR LA TENDENCIA
    // if (dataActas && dataActas.length > 0) {
    //     dibujarConsultaActas(dataActas); 
    // }

    // 🆕 5. Gráfico de Tendencia de Consulta de Actas (Línea/Área)
    if (dataTendenciaActas && dataTendenciaActas.length > 0) {
        // La función dibuja en 'graficoTendenciaActas', que ahora ocupa el espacio del Top 10.
        dibujarTendenciaActas(dataTendenciaActas); 
    }
}


// =========================================================
// 🆕 5. GRÁFICO DE TENDENCIA DE CONSULTA DE ACTAS (LÍNEA/ÁREA)
// =========================================================
function dibujarTendenciaActas(data) {
    // ID del canvas donde se dibujará el gráfico (el que reemplazó al Top 10)
    const ctx = document.getElementById('graficoTendenciaActas');
    // ⚠️ CHEQUEO CRÍTICO: Si el elemento no existe, salimos sin error
    if (!ctx) return; 
    
    // 1. Formatear los datos
    const labels = data.map(item => {
        const date = new Date(item.mes_consulta);
        return new Intl.DateTimeFormat('es-ES', { month: 'short', year: 'numeric' }).format(date);
    });
    
    const consultas = data.map(item => item.total_consultas);

    // 2. Inicializar el gráfico de Área/Línea
    new Chart(ctx, {
        type: 'line', 
        data: {
            labels: labels,
            datasets: [{
                label: 'Total de Consultas',
                data: consultas,
                backgroundColor: 'rgba(40, 123, 255, 0.3)', 
                borderColor: 'rgba(40, 123, 255, 1)',      
                borderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                tension: 0.4, 
                fill: true,   
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        title: (context) => context[0].label,
                        label: (context) => `Consultas: ${context.parsed.y.toLocaleString('es-ES')}`
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Mes de Consulta'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Número de Consultas'
                    },
                    // Asegura que las etiquetas sean enteras
                    ticks: {
                        callback: function(value) { 
                            if (value % 1 === 0) { 
                                return value.toLocaleString('es-ES'); 
                            } 
                        }
                    }
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
    if (!ctx) return; // Chequeo de nulidad
    
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
    if (!ctx) return; // Chequeo de nulidad
    
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
    if (!ctx) return; // Chequeo de nulidad
    
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
                    title: {
                        display: true,
                        text: 'Cantidad'
                    }
                }
            }
        }
    });
}


// =========================================================
// 4. GRÁFICO DE CONSULTA DE ACTAS TOP 10 (Función no llamada)
// =========================================================
function dibujarConsultaActas(data) {
    // Función mantenida por referencia, pero no llamada por inicializarGraficosBI
    const ctx = document.getElementById('graficoConsultaActas');
    if (!ctx) return;
    
    const labels = data.map(item => item.acta__titulo);
    const consultas = data.map(item => item.consultas);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Consultas',
                data: consultas,
                backgroundColor: 'rgba(40, 123, 255, 0.8)',
                borderColor: 'rgba(40, 123, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Veces Consultada' },
                    ticks: { callback: (value) => { if (value % 1 === 0) { return value; } } }
                },
                x: {
                    ticks: { autoSkip: true, maxRotation: 0, minRotation: 0 }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}