from django.urls import path
from .views import ComplaintListCreateView

urlpatterns = [
    path("", ComplaintListCreateView.as_view(), name="complaint_list_create"),
]
