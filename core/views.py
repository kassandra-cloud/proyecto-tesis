from django.shortcuts import render

def home(request):
    return render(request, "core/home.html", {"titulo": "Proyecto de Tesis funcionando"})

# Create your views here.
def sin_permiso(request):
    return render(request, "core/sin_permiso.html", status=403)