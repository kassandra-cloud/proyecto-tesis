from django.shortcuts import render

def taller_list(request):
    return render(request, "talleres/taller_list.html")

def taller_create(request):
    return render(request, "talleres/taller_form.html")

def inscripcion_list(request, pk):
    return render(request, "talleres/inscripcion_list.html", {"taller_id": pk})
