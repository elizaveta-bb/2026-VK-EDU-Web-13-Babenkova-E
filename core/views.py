from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.csrf import csrf_failure as django_csrf_failure
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, ProfileForm, SignupForm


login_view = LoginView.as_view(template_name="core/login.html", authentication_form=LoginForm)
logout_view = LogoutView.as_view()


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("questions:index")

    form = SignupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("questions:index")

    return render(request, "core/signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            return redirect("core:profile")
    else:
        form = ProfileForm(user=request.user)

    return render(request, "core/profile.html", {"form": form})


def csrf_failure(request, reason=""):
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(
            {"error": "Запрос не прошёл проверку CSRF. Обновите страницу и попробуйте снова."},
            status=403,
        )
    return django_csrf_failure(request, reason=reason)
