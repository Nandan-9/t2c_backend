from django.urls import path

from users.views.department_views import DepartmentDetailView, DepartmentListCreateView
from users.views.district_views import DistrictDetailView, DistrictListCreateView
from users.views.minister_views import (
    MinisterDetailView,
    MinisterFollowersView,
    MinisterFollowView,
    MinisterListCreateView,
    MinisterTagSearchView,
    MyFollowingView,
)
from users.views.user_views import UserMeView, UsernameCheckView

urlpatterns = [
    path("me/", UserMeView.as_view(), name="user-me"),
    path("me/username/check/", UsernameCheckView.as_view(), name="username-check"),
    path("me/following/", MyFollowingView.as_view(), name="my-following"),
    path("ministers/tags/", MinisterTagSearchView.as_view(), name="minister-tags"),
    path("ministers/", MinisterListCreateView.as_view(), name="minister-list-create"),
    path("ministers/<int:minister_id>/", MinisterDetailView.as_view(), name="minister-detail"),
    path("ministers/<int:minister_id>/follow/", MinisterFollowView.as_view(), name="minister-follow"),
    path("ministers/<int:minister_id>/followers/", MinisterFollowersView.as_view(), name="minister-followers"),
    path("departments/", DepartmentListCreateView.as_view(), name="department-list-create"),
    path("departments/<int:department_id>/", DepartmentDetailView.as_view(), name="department-detail"),
    path("districts/", DistrictListCreateView.as_view(), name="district-list-create"),
    path("districts/<int:district_id>/", DistrictDetailView.as_view(), name="district-detail"),
]
