/* static/js/public_utils.js */

document.addEventListener('DOMContentLoaded', function () {
    const toggles = document.querySelectorAll('.toggle-password');
    toggles.forEach(function (btn) {
      const targetSelector = btn.getAttribute('data-target');
      const input = targetSelector
        ? document.querySelector(targetSelector)
        : btn.closest('.position-relative, .input-group, form, body').querySelector('input[type="password"], input[type="text"][data-is-password]');
      
      if (!input) return;

      // Marca para identificar inputs revelados
      if (input.type === 'text') input.setAttribute('data-is-password', 'true');

      btn.addEventListener('click', function () {
        const icon = btn.querySelector('i');
        const isPassword = input.getAttribute('type') === 'password';
        input.setAttribute('type', isPassword ? 'text' : 'password');

        if (icon) {
          icon.classList.toggle('fa-eye', !isPassword);
          icon.classList.toggle('fa-eye-slash', isPassword);
        }
        btn.setAttribute('aria-label', isPassword ? 'Ocultar contraseña' : 'Mostrar contraseña');
        btn.setAttribute('title', isPassword ? 'Ocultar contraseña' : 'Mostrar contraseña');
      });
    });
});