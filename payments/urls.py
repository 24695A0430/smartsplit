from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('record/<int:group_id>/', views.record_payment_view, name='record'),
    path('checkout/<int:group_id>/<int:payee_id>/', views.checkout_view, name='checkout'),
    path('process/<int:group_id>/<int:payee_id>/', views.process_payment_view, name='process'),
    path('success/<int:payment_id>/', views.payment_success_view, name='success'),
    path('failed/<int:payment_id>/', views.payment_failed_view, name='failed'),
    path('checkout/expense/', views.checkout_expense_view, name='checkout_expense'),
    path('process/expense/', views.process_expense_payment_view, name='process_expense_payment'),
    path('history/', views.transaction_history_view, name='history'),
]
