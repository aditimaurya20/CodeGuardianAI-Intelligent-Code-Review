from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/',views.login_page,name="login"),
    path('register/', views.register_page, name="register"),
    path('upload/', views.upload_page, name="upload"),
    path('github/', views.github_project, name='github_project'),
    path('result/', views.result_page, name='result'),
    path('logout/', views.logout_page, name='logout'),
    path('history/', views.history_page, name='history'),
    path('history/<int:history_id>/', views.history_detail, name='history_detail'),
    path('github/download-pdf/',views.download_github_pdf,name='download_github_pdf'),
    path('result/download-pdf/',views.download_result_pdf,name='download_result_pdf'),
]