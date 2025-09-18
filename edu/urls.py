# edu/urls.py
from django.urls import path
from .views import (
    YearMe, StudentSemesters, StudentModules,
    StudentSubjects, StudentLessons, LessonDetail,StudentQuestions, StudentQuestionDetail,
    FlashCardListCreate , FlashCardDetail,FavoriteLessonList, FavoriteLessonAdd, FavoriteLessonRemove, FavoriteLessonIDs
)

urlpatterns = [
    path("api/v1/edu/years/me/", YearMe.as_view(), name="edu_year_me"),
    path("api/v1/edu/semesters/", StudentSemesters.as_view(), name="edu_semesters"),
    path("api/v1/edu/modules/", StudentModules.as_view(), name="edu_modules"),
    path("api/v1/edu/subjects/", StudentSubjects.as_view(), name="edu_subjects"),
    path("api/v1/edu/lessons/", StudentLessons.as_view(), name="edu_lessons"),
    path("api/v1/edu/lessons/<int:pk>/", LessonDetail.as_view(), name="edu_lesson_detail"),
    path("api/v1/edu/questions/", StudentQuestions.as_view(), name="edu_questions"),
    path("api/v1/edu/questions/<int:pk>/", StudentQuestionDetail.as_view(), name="edu_question_detail"),
    path("api/v1/edu/flashcards/", FlashCardListCreate.as_view(), name="edu_flashcards"),
    path("api/v1/edu/flashcards/<int:pk>/", FlashCardDetail.as_view(), name="edu_flashcard_detail"),

    path("api/v1/edu/favorites/lessons/", FavoriteLessonList.as_view(), name="edu_fav_lessons_list"),
    path("api/v1/edu/favorites/lessons/ids/", FavoriteLessonIDs.as_view(), name="edu_fav_lessons_ids"),
    path("api/v1/edu/favorites/lessons/add/", FavoriteLessonAdd.as_view(), name="edu_fav_lessons_add"),
    path("api/v1/edu/favorites/lessons/remove/", FavoriteLessonRemove.as_view(), name="edu_fav_lessons_remove"),
]
