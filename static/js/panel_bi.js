/* static/js/panel_bi.js */

/**
 * Inicializa los gráficos del dashboard.
 * Recibe los datos ya procesados desde el template.
 */
function inicializarGraficosBI(dataTalleres, dataActas, dataParticipacion, dataDemografia) {
    
    // --- 1. Gráfico Participación (Gauge/Doughnut) ---
    if (dataParticipacion.porcentaje_actual != null) {
        const ctxGauge = document.getElementById('graficoParticipacionGauge').getContext('2d');
        const pctActual = dataParticipacion.porcentaje_actual;
        const pctMeta = dataParticipacion.porcentaje_meta; 
        
        new Chart(ctxGauge, {
            type: 'doughnut',
            data: {
                labels: ['Alcanzado', 'Faltante para Meta'],
                datasets: [{
                    data: [
                        pctActual, 
                        Math.max(0, pctMeta - pctActual),
                    ],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.6)', // Turquesa
                        'rgba(255, 99, 132, 0.6)', // Rosa
                    ]
                }]
            },
            options: {
                responsive: true,
                circumference: 180, 
                rotation: -90,      
                plugins: {
                    tooltip: { enabled: true },
                    legend: { display: true }
                }
            }
        });
    }

    // --- 2. Gráfico: Distribución Demográfica (Torta) ---
    const ctxDemografia = document.getElementById('graficoDemografiaSector').getContext('2d');
    new Chart(ctxDemografia, {
        type: 'pie',
        data: {
            labels: dataDemografia.map(d => d.direccion_sector || 'No especificado'),
            datasets: [{
                label: 'Total Vecinos',
                data: dataDemografia.map(d => d.total_vecinos),
                backgroundColor: dataDemografia.map(() => `rgba(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, 0.6)`)
            }]
        },
        options: { 
            responsive: true,
            plugins: {
                legend: { position: 'top' }
            }
        }
    });
    
    // --- 3. Gráfico Ocupación Talleres (Barras) ---
    const ctxTalleres = document.getElementById('graficoOcupacionTalleres').getContext('2d');
    new Chart(ctxTalleres, {
        type: 'bar',
        data: {
            labels: dataTalleres.map(d => d.nombre),
            datasets: [
                {
                    label: 'Inscritos',
                    data: dataTalleres.map(d => d.inscritos),
                    backgroundColor: 'rgba(255, 159, 64, 0.6)'
                },
                {
                    label: 'Cupos Totales',
                    data: dataTalleres.map(d => d.cupos),
                    backgroundColor: 'rgba(201, 203, 207, 0.6)'
                }
            ]
        },
        options: { responsive: true }
    });
    
    // --- 4. Gráfico Tasa de Consulta de Actas (Barras) ---
    const ctxActas = document.getElementById('graficoConsultaActas').getContext('2d');
    new Chart(ctxActas, {
        type: 'bar',
        data: {
            labels: dataActas.map(d => d.acta__titulo),
            datasets: [{
                label: 'Total Consultas',
                data: dataActas.map(d => d.consultas),
                backgroundColor: 'rgba(153, 102, 255, 0.6)'
            }]
        },
        options: { responsive: true }
    });
}