"""
--------------------------------------------------------------------------------
Integrantes:           Matias Pinilla, Herna Leris, Kassandra Ramos
Fecha de Modificación: 19/12/2025
Descripción:           Contiene las vistas (controladores) de la aplicación.
                       Maneja el listado (con caché), la creación, edición y 
                       eliminación de anuncios, así como la interacción con 
                       los formularios y plantillas.
--------------------------------------------------------------------------------
"""

# Importa atajos comunes de Django: renderizar templates, redireccionar, obtener objetos o error 404.
from django.shortcuts import render, redirect, get_object_or_404
# Importa el decorador para requerir que el usuario esté logueado.
from django.contrib.auth.decorators import login_required
# Importa el sistema de mensajes flash para notificaciones al usuario.
from django.contrib import messages
# Importa el decorador de caché para optimizar el rendimiento de la vista.
from django.views.decorators.cache import cache_page
# Importa el modelo y el formulario locales.
from .models import Anuncio
from .forms import AnuncioForm

# Aplica caché de 60 segundos a la vista y requiere inicio de sesión.
@cache_page(60)
@login_required
def lista_anuncios(request):
    """
    Muestra todos los anuncios enviados.
    Usa caché (Redis) y optimización SQL select_related.
    """
    # Consulta todos los anuncios cargando anticipadamente el autor (JOIN SQL).
    anuncios = Anuncio.objects.select_related('autor').all()

    # Crea una instancia vacía del formulario para usarla en el modal de creación rápida.
    form = AnuncioForm() 

    # Prepara el contexto de datos para la plantilla.
    context = {
        'anuncios': anuncios,
        'form': form, 
    }
    # Renderiza la plantilla HTML con los datos.
    return render(request, 'anuncios/lista_anuncios.html', context)

@login_required
def crear_anuncio(request):
    """Maneja la creación de un nuevo anuncio."""
    # Verifica si la petición es POST (envío de datos).
    if request.method == 'POST':
        # Rellena el formulario con los datos recibidos.
        form = AnuncioForm(request.POST)
        # Valida los datos.
        if form.is_valid():
            # Crea el objeto en memoria sin guardarlo aún en BD.
            anuncio = form.save(commit=False)
            # Asigna el usuario actual como autor.
            anuncio.autor = request.user 
            # Guarda definitivamente en la BD. Esto dispara la señal post_save (notificaciones).
            anuncio.save()
            
            # Envía mensaje de éxito.
            messages.success(request, 'Anuncio enviado exitosamente.')
            # Redirige a la lista de anuncios.
            return redirect('anuncios:lista_anuncios')
    else:
        # Si es GET, crea un formulario vacío.
        form = AnuncioForm()

    context = {
        'form': form,
        'anuncio': None # Indica a la plantilla que es una creación nueva.
    }
    return render(request, 'anuncios/crear_anuncio.html', context)

@login_required
def editar_anuncio(request, pk):
    """Maneja la edición de un anuncio existente identificado por su PK (ID)."""
    # Obtiene el anuncio o lanza error 404 si no existe.
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.method == 'POST':
        # Carga el formulario con los datos nuevos (POST) y la instancia existente.
        form = AnuncioForm(request.POST, instance=anuncio)
        if form.is_valid():
            # Guarda los cambios.
            form.save()
            messages.success(request, 'Anuncio actualizado exitosamente.')
            return redirect('anuncios:lista_anuncios')
    else:
        # Si es GET, carga el formulario con los datos actuales del anuncio.
        form = AnuncioForm(instance=anuncio)

    context = {
        'form': form,
        'anuncio': anuncio # Indica a la plantilla que estamos editando este objeto.
    }
    # Reutiliza la plantilla de creación.
    return render(request, 'anuncios/crear_anuncio.html', context)

@login_required
def eliminar_anuncio(request, pk):
    """Maneja la eliminación de un anuncio."""
    anuncio = get_object_or_404(Anuncio, pk=pk)

    if request.method == 'POST':
        # Si el usuario confirma (envía formulario POST), procedemos a borrar.
        titulo_anuncio = anuncio.titulo
        anuncio.delete()
        messages.success(request, f'El anuncio "{titulo_anuncio}" ha sido eliminado.')
        return redirect('anuncios:lista_anuncios')
    
    # Si es GET, mostramos la página de confirmación de borrado.
    context = {
        'anuncio': anuncio
    }
    return render(request, 'anuncios/confirmar_eliminar.html', context)