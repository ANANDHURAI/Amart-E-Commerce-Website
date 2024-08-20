from django.urls import path
from . import views

urlpatterns = [
    path('razorpay-order-creation/<amount>/', views.razorpay_order_creation, name="razorpay_order_creation"),
	path('razorpay-paymenthandler/', views.razorpay_paymenthandler, name='razorpay_paymenthandler'),
    path('cash-on-delivery', views.cash_on_delivery, name="cash_on_delivery"),
    path('pay-now/<order_id>/', views.pay_now, name="pay_now"),
    path('payment-success', views.payment_success, name="payment_success"),
]