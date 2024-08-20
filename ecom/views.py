from django.shortcuts import render


def get_next_url(request):
    next_url = request.META.get("HTTP_REFERER")
    return next_url



def custom_404(request, exception):
    return render(request, "home/404.html", {})

