"""URL configuration for the iDrug Django project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView

from web.views import (
    ComplexView,
    DTI,
    DrugView,
    LoginView,
    PredictionModelsRunView,
    ProteinView,
    RegisterView,
    current_user_view,
    data_sources_summary,
    logout_view,
    personalization_options,
    personalized_recommend,
    save_recommendation_result,
    saved_recommendation_delete,
    saved_recommendation_detail,
    saved_recommendation_list,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", logout_view),
    path("drugApi/", DrugView.as_view()),
    path("pdbApi/", ProteinView.as_view()),
    path("complexApi/", ComplexView.as_view()),
    path("dti/", DTI.as_view()),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("home.html", TemplateView.as_view(template_name="home.html"), name="home_page"),
    path("Function.html", TemplateView.as_view(template_name="Function.html")),
    path("prediction_models.html", TemplateView.as_view(template_name="prediction_models.html")),
    path("data_sources.html", TemplateView.as_view(template_name="data_sources.html")),
    path("tutorial.html", TemplateView.as_view(template_name="tutorial.html")),
    path("plat_DTI_input.html", TemplateView.as_view(template_name="plat_DTI_input.html")),
    path("plat_DTI_result.html", TemplateView.as_view(template_name="plat_DTI_result.html")),
    path("saved_results.html", TemplateView.as_view(template_name="saved_results.html")),
    path("saved_result_detail.html", TemplateView.as_view(template_name="saved_result_detail.html")),
    path("login.html", TemplateView.as_view(template_name="login.html")),
    path("signUp.html", TemplateView.as_view(template_name="signUp.html")),
    path("userInfo.html", TemplateView.as_view(template_name="userInfo.html")),
    path("api/current-user/", current_user_view, name="current_user"),
    path("api/data-sources/summary/", data_sources_summary, name="data_sources_summary"),
    path("api/prediction-models/run/", PredictionModelsRunView.as_view(), name="prediction_models_run"),
    path("api/personalization-options/", personalization_options, name="personalization_options"),
    path("api/saved-recommendations/", saved_recommendation_list, name="saved_recommendation_list"),
    path("api/saved-recommendations/<str:save_id>/", saved_recommendation_detail, name="saved_recommendation_detail"),
    path("api/saved-recommendations/<str:save_id>/delete/", saved_recommendation_delete, name="saved_recommendation_delete"),
    path("api/save-recommendation/", save_recommendation_result, name="save_recommendation_result"),
    path("api/personalized_recommend/", personalized_recommend, name="personalized_recommend"),
]

if settings.DEBUG:
    urlpatterns += static("/pic/", document_root=settings.BASE_DIR / "pic")
