from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="web_login"),
    path("logout/", views.logout_view, name="web_logout"),
    path("register/", views.register_view, name="web_register"),
    
    path("", views.home, name="web_home"),
    path("pomodoro/log/", views.pomodoro_log, name="pomodoro_log"),

    path("materials/", views.materials_home, name="web_materials_home"),
    path("materials/favorites/lessons/<int:lesson_id>/toggle/",views.favorite_lesson_toggle,name="favorite_lesson_toggle",),

    path("questions/", views.questions_home, name="web_questions_home"),
    path("flashcards/", views.flashcards_home, name="web_flashcards_home"),
    path("planner/", views.planner_home, name="web_planner_home"),
    path("profile/", views.profile_home, name="web_profile_home"),
]
