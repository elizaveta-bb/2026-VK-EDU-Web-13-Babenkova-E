from django.shortcuts import render


def login_view(request):
    return render(request, "core/login.html")


def signup_view(request):
    return render(request, "core/signup.html")


def profile_view(request):
    profile = {
        "username": "elizaveta",
        "email": "elizaveta@example.com",
        "display_name": "Елизавета",
    }

    return render(
        request,
        "core/profile.html",
        {"profile": profile},
    )