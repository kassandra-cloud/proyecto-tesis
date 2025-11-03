# foro/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Publicacion, ArchivoAdjunto
from .forms import PublicacionForm

@login_required
def lista_publicaciones(request):
    publicaciones = Publicacion.objects.all().prefetch_related('adjuntos')
    
    form_con_error_data = request.session.pop('form_con_error_data', None)
    form_errors = request.session.pop('form_errors', None)
    
    if form_con_error_data:
        form = PublicacionForm(form_con_error_data)
        if form_errors:
            form.add_error(None, form_errors)
    else:
        form = PublicacionForm()

    context = {
        'publicaciones': publicaciones,
        'form': form,
        'form_errors_manual': form_errors
    }
    return render(request, 'foro/lista_publicaciones.html', context)


@login_required
def crear_publicacion(request):
    if request.method != 'POST':
        return redirect('lista_publicaciones')

    print("\n--- [DEPURACIÓN: CREAR_PUBLICACIÓN] ---")
    print("request.POST:", request.POST)
    print("request.FILES:", request.FILES)

    form = PublicacionForm(request.POST)

    if form.is_valid():
        publicacion = form.save(commit=False)
        publicacion.autor = request.user
        publicacion.save()

        # Archivos subidos (videos, imágenes, audios, etc.)
        files_list = request.FILES.getlist('archivos')
        for f in files_list:
            print(f"Guardando archivo: {f.name}")
            ArchivoAdjunto.objects.create(publicacion=publicacion, archivo=f)

        return redirect('lista_publicaciones')
    
    else:
        print("Errores del formulario:", form.errors.as_json())
        request.session['form_con_error_data'] = request.POST
        request.session['form_errors'] = form.errors.as_json()
        return redirect('lista_publicaciones')
