from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, reverse

def homepage(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse('accounts:dashboard'))
        else:
            return render(request, 'index.html', {})