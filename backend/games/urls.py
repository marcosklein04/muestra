from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path("", views.home, name="home"),
    path("jugar/<slug:slug>/", views.runner_page, name="runner_page"),

    # Session API (called by game JS)
    path("api/sesion/iniciar/<slug:slug>/", views.api_iniciar_sesion, name="api_iniciar_sesion"),
    path("runner/sesiones/<uuid:session_id>", views.runner_obtener_sesion, name="runner_obtener_sesion"),
    path("runner/sesiones/<uuid:session_id>/finalizar", views.runner_finalizar_sesion, name="runner_finalizar_sesion"),
]
