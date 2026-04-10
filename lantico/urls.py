from django.contrib import admin
from django.urls import path
from test_app import views
from test_app.views_pdf import result_pdf

urlpatterns = [
    # Pages (HTML)
    path("", views.landing_page, name="landing"),
    path("test/", views.test_page, name="test"),
    path("result/<uuid:session_id>/", views.result_page, name="result"),

    # API (JSON)
    path("api/questions/", views.questions_list),
    path("api/submit_test/", views.submit_test),
    path("api/result/<uuid:session_id>/", views.result_detail),
    path("api/result/<uuid:session_id>/pdf/", result_pdf),

    path("admin/", admin.site.urls),
]
