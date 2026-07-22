from django.urls import path
from . import views

app_name = 'settlements'

urlpatterns = [
    path('group/<int:group_id>/', views.group_settlements_view, name='dashboard'),
    path('approve/<int:settlement_id>/', views.approve_settlement_view, name='approve'),
    path('reject/<int:settlement_id>/', views.reject_settlement_view, name='reject'),
]
