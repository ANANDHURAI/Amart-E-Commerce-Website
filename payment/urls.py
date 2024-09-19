from django.urls import path
from . import views

urlpatterns = [
    path(
        "razorpay-order-creation/<int:amount>/",
        views.razorpay_order_creation,
        name="razorpay_order_creation",
    ),
    path(
        "razorpay-payment-handler/",
        views.razorpay_paymenthandler,
        name="razorpay_paymenthandler",
    ),
    path("cash-on-delivery/", views.cash_on_delivery, name="cash_on_delivery"),
    path("pay-now/<int:order_id>/", views.pay_now, name="pay_now"),
    path("payment-success/", views.payment_success, name="payment_success"),
    path(
        "wallet/recharge/complete/",
        views.wallet_recharge_complete,
        name="wallet_recharge_complete",
    ),
    path("razorpay-callback/", views.razorpay_callback, name="razorpay_callback"),
    path("payment/failed/<str:order_id>/", views.payment_failed, name="payment_failed"),
    path("payment/failed/", views.payment_failed, name="payment_failed"),
    path(
        "wallet-payment-complete/",
        views.wallet_payment_complete,
        name="wallet_payment_complete",
    ),
    # path('customer_wallet/', views.customer_wallet, name='customer_wallet'),
    path("payment/failed/", views.payment_failed, name="payment_failed"),
]
