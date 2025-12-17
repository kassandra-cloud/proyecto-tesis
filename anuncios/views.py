from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# --- IMPORTACIÓN CRÍTICA PARA CACHÉ ---
from django.views.decorators.cache import cache_page
# -------------------------------------
from .models import Anuncio
from .forms import AnuncioForm
# Ya no necesitamos importar Perfil ni la función 'es_directiva'

# OPTIMIZACIÓN: Aplicamos caché de 60 segundos
@cache_page(60)
@login_required
def lista_anuncios(request):
    """
    Muestra todos los anuncios enviados.
    Optimizado con:
    1. @cache_page(60) para servir la página desde Redis.
    2. .select_related('autor') para evitar el problema de consultas N+1.
    """
    # Optimización de consulta: Precargar la información del autor
    anuncios = Anuncio.objects.select_related('autor').all()

    # --- LÍNEA AÑADIDA ---
    form = AnuncioForm() # Formulario vacío para el modal de "Crear"

    context = {
        'anuncios': anuncios,
        'form': form, # --- LÍNEA AÑADIDA ---
    }
    return render(request, 'anuncios/lista_anuncios.html', context)

@login_required
def crear_anuncio(request):
    # NOTA: Las vistas POST no se cachean
    if request.method == 'POST':
        form = AnuncioForm(request.POST)
        if form.is_valid():
            anuncio = form.save(commit=False)
            anuncio.autor = request.user 
            # Al ejecutar .save(), Django disparará automáticamente
            # la señal 'post_save' definida en signals.py, enviando la notificación.
            # (El envío de notificación debería ser una tarea Celery para offloading)
            anuncio.save()
            
            messages.success(request, 'Anuncio enviado exitosamente.')
            return redirect('anuncios:lista_anuncios')
    else:
        form = AnuncioForm()

    context = {
        'form': form,
        'anuncio': None # Para que el template sepa que estamos "Creando"
    }
    return render(request, 'anuncios/crear_anuncio.html', context)

# --- VISTA NUEVA PARA EDITAR ---
@login_required
def editar_anuncio(request, pk):
    """
    Formulario para editar un anuncio existente.
    """
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.method == 'POST':
        form = AnuncioForm(request.POST, instance=anuncio)
        if form.is_valid():
            form.save()
            messages.success(request, 'Anuncio actualizado exitosamente.')
            return redirect('anuncios:lista_anuncios')
    else:
        form = AnuncioForm(instance=anuncio)

    context = {
        'form': form,
        'anuncio': anuncio # Para que el template sepa que estamos "Editando"
    }
    # Reutilizamos la plantilla de creación
    return render(request, 'anuncios/crear_anuncio.html', context)


# --- VISTA NUEVA PARA ELIMINAR ---
@login_required
def eliminar_anuncio(request, pk):
    """
    Página de confirmación para eliminar un anuncio.
    """
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.method == 'POST':
        # Si el usuario confirma (hace POST), borramos
        titulo_anuncio = anuncio.titulo
        anuncio.delete()
        messages.success(request, f'El anuncio "{titulo_anuncio}" ha sido eliminado.')
        return redirect('anuncios:lista_anuncios')
    
    # Si es GET, mostramos la página de confirmación
    context = {
        'anuncio': anuncio
    }
    return render(request, 'anuncios/confirmar_eliminar.html', context)