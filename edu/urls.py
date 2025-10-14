# edu/urls.py
from django.urls import path
from .views import (
    YearMe, StudentSemesters, StudentModules,
    StudentSubjects, StudentLessons, LessonDetail,StudentQuestions, StudentQuestionDetail,
    FlashCardListCreate , FlashCardDetail,FavoriteLessonList, FavoriteLessonAdd, FavoriteLessonRemove, 
    FavoriteLessonIDs ,FlashcardCountView,LessonProgressCountView ,LessonMarkDoneView,
    PlannerTaskListCreate,PlannerToday,PlannerMarkDone,PlannerMarkUndone,PlannerDelete,StreakMessageView,LessonProgressIDs,StudentChapters
)

# urlpatterns = [
#     path("api/v1/edu/years/me/", YearMe.as_view(), name="edu_year_me"),
#     path("api/v1/edu/semesters/", StudentSemesters.as_view(), name="edu_semesters"),
#     path("api/v1/edu/modules/", StudentModules.as_view(), name="edu_modules"),
#     path("api/v1/edu/subjects/", StudentSubjects.as_view(), name="edu_subjects"),
#     path("api/v1/edu/lessons/", StudentLessons.as_view(), name="edu_lessons"),
#     path("api/v1/edu/lessons/<int:pk>/", LessonDetail.as_view(), name="edu_lesson_detail"),
#     path("api/v1/edu/questions/", StudentQuestions.as_view(), name="edu_questions"),
#     path("api/v1/edu/questions/<int:pk>/", StudentQuestionDetail.as_view(), name="edu_question_detail"),
#     path("api/v1/edu/flashcards/", FlashCardListCreate.as_view(), name="edu_flashcards"),
#     path("api/v1/edu/flashcards/<int:pk>/", FlashCardDetail.as_view(), name="edu_flashcard_detail"),
#     # count
#     path("flashcards/count/", FlashcardCountView.as_view()),
#     path("lessons/progress/count/", LessonProgressCountView.as_view()),
#     # mark lesson done
#     path("lessons/<int:lesson_id>/progress/done/", LessonMarkDoneView.as_view()),

#     # activities followin up
#     path("streak/message/", StreakMessageView.as_view()),

#     # planner
#     path("planner/tasks/", PlannerTaskListCreate.as_view()),
#     path("planner/tasks/today/", PlannerToday.as_view()),
#     path("planner/tasks/<int:pk>/done/", PlannerMarkDone.as_view()),
#     path("planner/tasks/<int:pk>/undone/", PlannerMarkUndone.as_view()),
#     path("planner/tasks/<int:pk>/", PlannerDelete.as_view()),

#     # favoirit
#     path("api/v1/edu/favorites/lessons/", FavoriteLessonList.as_view(), name="edu_fav_lessons_list"),
#     path("api/v1/edu/favorites/lessons/ids/", FavoriteLessonIDs.as_view(), name="edu_fav_lessons_ids"),
#     path("api/v1/edu/favorites/lessons/add/", FavoriteLessonAdd.as_view(), name="edu_fav_lessons_add"),
#     path("api/v1/edu/favorites/lessons/remove/", FavoriteLessonRemove.as_view(), name="edu_fav_lessons_remove"),
# ]
urlpatterns = [
    path("api/v1/edu/years/me/", YearMe.as_view(), name="edu_year_me"),
    path("api/v1/edu/semesters/", StudentSemesters.as_view(), name="edu_semesters"),
    path("api/v1/edu/modules/", StudentModules.as_view(), name="edu_modules"),
    path("api/v1/edu/subjects/", StudentSubjects.as_view(), name="edu_subjects"),
    path("api/v1/edu/chapters/", StudentChapters.as_view(), name="edu_chapters"),
    path("api/v1/edu/lessons/", StudentLessons.as_view(), name="edu_lessons"),
    path("api/v1/edu/lessons/<int:pk>/", LessonDetail.as_view(), name="edu_lesson_detail"),
    path("api/v1/edu/questions/", StudentQuestions.as_view(), name="edu_questions"),
    path("api/v1/edu/questions/<int:pk>/", StudentQuestionDetail.as_view(), name="edu_question_detail"),
    path("api/v1/edu/flashcards/", FlashCardListCreate.as_view(), name="edu_flashcards"),
    path("api/v1/edu/flashcards/<int:pk>/", FlashCardDetail.as_view(), name="edu_flashcard_detail"),

    # flashcards count
    path("api/v1/edu/flashcards/count/", FlashcardCountView.as_view(), name="edu_flashcards_count"),

    # lessons progress
    path("api/v1/edu/lessons/progress/count/", LessonProgressCountView.as_view(), name="edu_lessons_progress_count"),
    path("api/v1/edu/lessons/<int:lesson_id>/progress/done/", LessonMarkDoneView.as_view(), name="edu_lessons_progress_done"),
    # edu/urls.py
    path("api/v1/edu/lessons/progress/ids/", LessonProgressIDs.as_view(), name="edu_lessons_progress_ids"),


    # streak
    path("api/v1/edu/streak/message/", StreakMessageView.as_view(), name="edu_streak_message"),

    # planner
    path("api/v1/edu/planner/tasks/", PlannerTaskListCreate.as_view(), name="edu_planner_tasks"),
    path("api/v1/edu/planner/tasks/today/", PlannerToday.as_view(), name="edu_planner_tasks_today"),
    path("api/v1/edu/planner/tasks/<int:pk>/done/", PlannerMarkDone.as_view(), name="edu_planner_task_done"),
    path("api/v1/edu/planner/tasks/<int:pk>/undone/", PlannerMarkUndone.as_view(), name="edu_planner_task_undone"),
    path("api/v1/edu/planner/tasks/<int:pk>/", PlannerDelete.as_view(), name="edu_planner_task_delete"),

    # favorites
    path("api/v1/edu/favorites/lessons/", FavoriteLessonList.as_view(), name="edu_fav_lessons_list"),
    path("api/v1/edu/favorites/lessons/ids/", FavoriteLessonIDs.as_view(), name="edu_fav_lessons_ids"),
    path("api/v1/edu/favorites/lessons/add/", FavoriteLessonAdd.as_view(), name="edu_fav_lessons_add"),
    path("api/v1/edu/favorites/lessons/remove/", FavoriteLessonRemove.as_view(), name="edu_fav_lessons_remove"),
]
