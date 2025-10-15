// static/password-meter.js
(function () {
  function evaluate(pw) {
    return {
      len: pw.length >= 12,
      lower: /[a-z]/.test(pw),
      upper: /[A-Z]/.test(pw),
      sym: /[^A-Za-z0-9]/.test(pw),
    };
  }

  function setItem(el, ok) {
    if (!el) return;
    el.classList.toggle('text-success', ok);
    el.classList.toggle('text-danger', !ok);
    const icon = el.querySelector('.pm-icon');
    if (icon) icon.textContent = ok ? '✔' : '✖';
  }

  function allTrue(obj) {
    return Object.values(obj).every(Boolean);
  }

  function updateChecklist(pw, prefix) {
    const r = evaluate(pw);
    setItem(document.getElementById(prefix + 'len'), r.len);
    setItem(document.getElementById(prefix + 'lower'), r.lower);
    setItem(document.getElementById(prefix + 'upper'), r.upper);
    setItem(document.getElementById(prefix + 'sym'), r.sym);
    return r;
  }

  function updateMatch(pw1, pw2) {
    const el = document.getElementById('pw-match');
    if (!el) return false;
    const ok = pw1.length > 0 && pw1 === pw2;
    el.innerHTML = ok
      ? '<span class="text-success">✔ Las contraseñas coinciden.</span>'
      : '<span class="text-danger">✖ Las contraseñas no coinciden.</span>';
    return ok;
  }

  function toggleSubmit(enabled) {
    const btn = document.getElementById('btn-guardar');
    if (btn) btn.disabled = !enabled;
  }

  function wireUpCreate() {
    const p1 = document.getElementById('id_password1');
    const p2 = document.getElementById('id_password2');
    if (!p1 || !p2) {
      // Si no estamos en el form de crear (ej. editar), habilita el botón
      toggleSubmit(true);
      return;
    }
    const prefix = 'pm-create-';
    const onChange = () => {
      const reqs = updateChecklist(p1.value, prefix);
      const match = updateMatch(p1.value, p2.value);
      toggleSubmit(allTrue(reqs) && match);
    };
    p1.addEventListener('input', onChange);
    p2.addEventListener('input', onChange);
    onChange(); // init
  }

  window.addEventListener('DOMContentLoaded', function () {
    wireUpCreate();
  });
})();
