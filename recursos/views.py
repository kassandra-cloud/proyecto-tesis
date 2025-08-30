from django.shortcuts import render

def recurso_list(request):
    return render(request, "recursos/recurso_list.html")

def recurso_create(request):
    return render(request, "recursos/recurso_form.html")
