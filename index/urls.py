from django.urls import path
from .views import *
from django.contrib.auth.views import LoginView, LogoutView
urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(template_name='signin.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
