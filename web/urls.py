from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="web_login"),
    path("logout/", views.logout_view, name="web_logout"),
    path("register/", views.register_view, name="web_register"),

    path("", views.landing_page, name="landing_page"),
    path("home/", views.home, name="web_home"),
    
    path("pomodoro/log/", views.pomodoro_log, name="pomodoro_log"),
    
    path("materials/favorites/", views.web_favorite_lessons, name="web_favorite_lessons"),
    path("materials/done/", views.web_done_lessons, name="web_done_lessons"),

    path("materials/", views.materials_home, name="web_materials_home"),
    path("materials/favorites/lessons/<int:lesson_id>/toggle/",views.favorite_lesson_toggle,name="favorite_lesson_toggle",),
    path("materials/lessons/<int:lesson_id>/done/", views.mark_lesson_done, name="web_mark_lesson_done"),
   
    path("materials/lesson/<int:lesson_id>/", views.materials_lesson, name="web_lesson"),
    
    # web/urls.py
    path("materials/lesson/<int:lesson_id>/questions/", views.lesson_questions_list, name="web_lesson_questions"),
    path("materials/questions/<int:pk>/", views.question_detail_htmx, name="web_question_detail"),
    path("materials/questions/<int:pk>/attempt/", views.web_question_attempt, name="web_question_attempt"),
    path("materials/questions/<int:pk>/reveal/",  views.web_question_reveal,  name="web_question_reveal"),
    
    # flashcards per lesson
    path("materials/lesson/<int:lesson_id>/flashcards/", views.web_flashcards_panel, name="web_flashcards_panel"),
    path("materials/lesson/<int:lesson_id>/flashcards/create/", views.web_flashcards_create, name="web_flashcards_create"),
    path("materials/flashcards/<int:pk>/delete/", views.web_flashcard_delete, name="web_flashcard_delete"),
    path("materials/flashcards/<int:pk>/update/",views.web_flashcard_update,name="web_flashcard_update"),


    # صفحة الاستكشاف
    path("questions/", views.web_questions_browse, name="web_questions_browse"),

    # NAV (يسار)
    path("questions/nav/semesters/", views.q_nav_semesters, name="q_nav_semesters"),
    path("questions/nav/modules/",   views.q_nav_modules,   name="q_nav_modules"),

      # البانلات
    path("questions/panel/module/", views.q_panel_module_hub, name="q_panel_module_hub"),
    path("questions/panel/old/", views.q_panel_old_hub, name="q_panel_old_hub"),
    path("questions/panel/examreview/", views.q_panel_examreview_hub, name="q_panel_examreview_hub"),
    path("questions/panel/years/", views.q_panel_years, name="q_panel_years"),
    path("questions/panel/subjects/", views.q_panel_subjects, name="q_panel_subjects"),

    # الجديد: اختيار النظري/العملي بعد المادة
    path("questions/panel/parts/", views.q_panel_parts, name="q_panel_parts"),

    # جديد: الشابترز والدروس
    path("questions/panel/chapters/", views.q_panel_chapters, name="q_panel_chapters"),
    path("questions/panel/lessons/", views.q_panel_lessons, name="q_panel_lessons"),

    # عرض الأسئلة
    path("questions/panel/questions/", views.q_panel_questions, name="q_panel_questions"),
    path("questions/list/", views.web_questions_list, name="web_questions_list"),
    
    
    # flashcards urls
    path("flashcards/", views.web_flashcards_browse, name="web_flashcards"),

    path("flashcards/nav/semesters/", views.fc_nav_semesters, name="fc_nav_semesters"),
    path("flashcards/nav/modules/",   views.fc_nav_modules,   name="fc_nav_modules"),

    path("flashcards/panel/subjects/",    views.fc_panel_subjects,    name="fc_panel_subjects"),
    path("flashcards/panel/chapters/", views.fc_panel_chapters, name="fc_panel_chapters"),

    path("flashcards/panel/lessons/",     views.fc_panel_lessons,     name="fc_panel_lessons"),
    path("flashcards/panel/flashcards/",  views.fc_panel_flashcards,  name="fc_panel_flashcards"),
    
  path(
    "flashcards/lesson/<int:lesson_id>/create/",
    views.web_flashcards_create_browse,
    name="web_flashcards_create_browse",
),

    
    # planner urls
    path("planner/", views.web_planner, name="web_planner"),
    path("planner/tasks/", views.planner_tasks_htmx, name="web_planner_tasks"),
    path("planner/tasks/create/", views.planner_task_create_htmx, name="web_planner_create"),
    path("planner/tasks/<int:pk>/toggle/", views.planner_task_toggle_htmx, name="web_planner_toggle"),
    path("planner/tasks/<int:pk>/delete/", views.planner_task_delete_htmx, name="web_planner_delete"),


    path("profile/", views.web_profile, name="web_profile"),
    # path("profile/info/", views.web_profile_info_htmx, name="web_profile_info"),  
    
    
    path("plans/", views.web_plans, name="web_plans"),
    path("plans/purchase/", views.web_plans_purchase, name="web_plans_purchase"),
    path("plans/start-trial/", views.web_plans_start_trial, name="web_plans_start_trial"),
    
    path("payments/instapay/", views.web_payment_page, name="web_payment_page"),
    path("payments/confirm/", views.web_payment_confirm, name="web_payment_confirm"),
    path("payments/coupon-validate/", views.web_coupon_validate, name="web_coupon_validate"),
    
    
    # AI
    path("ai/ask/", views.web_ai_ask, name="web_ai_ask"),





]
