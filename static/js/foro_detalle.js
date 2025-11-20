/* static/js/foro_detalle.js */

document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-reply]');
    if (!btn) return;
    e.preventDefault();
    const id = btn.getAttribute('data-reply');
    const form = document.getElementById('reply-form-' + id);
    if (form) {
        form.style.display = (form.style.display === 'none' || !form.style.display) ? 'block' : 'none';
    }
});