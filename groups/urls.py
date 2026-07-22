from django.urls import path
from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.group_list_view, name='list'),
    path('create/', views.group_create_view, name='create'),
    path('<int:group_id>/', views.group_detail_view, name='detail'),
    path('<int:group_id>/edit/', views.group_edit_view, name='edit'),
    path('<int:group_id>/delete/', views.group_delete_view, name='delete'),
    path('join/', views.join_group_code_view, name='join_code'),
    path('join/<str:invite_code>/', views.join_group_link_view, name='join_link'),
    path('<int:group_id>/leave/', views.leave_group_view, name='leave'),
    path('<int:group_id>/remove/<int:user_id>/', views.remove_member_view, name='remove_member'),
]
