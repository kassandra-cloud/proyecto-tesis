(function () {
  function soloLetrasEspacios(ev) {
    // Elimina números y símbolos, permite letras (incluye acentos) y espacios
    ev.target.value = ev.target.value.normalize("NFD")
      .replace(/[^A-Za-z\u00C0-\u017F\s]/g, "") // borra todo excepto letras latinas/acento y espacio
      .replace(/\s{2,}/g, " "); // colapsa múltiples espacios
  }

  function dvMod11(cuerpoStr) {
    let suma = 0, mult = 2;
    for (let i = cuerpoStr.length - 1; i >= 0; i--) {
      suma += parseInt(cuerpoStr[i], 10) * mult;
      mult = mult === 7 ? 2 : mult + 1;
    }
    const resto = 11 - (suma % 11);
    if (resto === 11) return '0';
    if (resto === 10) return 'K';
    return String(resto);
  }

  function actualizarDV() {
    const cuerpo = rutCuerpo.value.replace(/\D/g, ""); // solo dígitos
    if (cuerpo.length >= 7 && cuerpo.length <= 9) {
      rutDv.value = dvMod11(cuerpo);
    } else {
      rutDv.value = "";
    }
  }

  window.addEventListener('DOMContentLoaded', function () {
    const first = document.getElementById('id_first_name');
    const last  = document.getElementById('id_last_name');
    rutCuerpo   = document.getElementById('id_rut_cuerpo');
    rutDv       = document.getElementById('id_rut_dv');

    if (first) first.addEventListener('input', soloLetrasEspacios);
    if (last)  last.addEventListener('input', soloLetrasEspacios);

    if (rutCuerpo && rutDv) {
      rutCuerpo.addEventListener('input', function () {
        // Solo números en el cuerpo
        rutCuerpo.value = rutCuerpo.value.replace(/\D/g, '');
        actualizarDV();
      });
      // Inicializa DV si ya hay valor (modo edición)
      actualizarDV();
    }
  });
})();
