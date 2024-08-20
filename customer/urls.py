from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="customer_dashboard"),
    path("orders", views.orders, name="customer_orders"),
    path("address", views.address, name="customer_address"),
    path("profile", views.profile, name="customer_profile"),
    path("edit-profile", views.edit_profile, name="edit_profile"),
    path("change-password", views.change_password, name="change_password"),
    path("cart", views.cart, name="cart"),
    path("favourites", views.favourites, name="favourites"),
    path("add-to-cart/<product_id>/", views.add_to_cart, name="add_to_cart"),
    path(
        "add-to-favourite/<product_id>/",
        views.add_to_favourite,
        name="add_to_favourite",
    ),
    path(
        "update-cart-item/<cart_item_id>/",
        views.update_cart_item,
        name="update_cart_item",
    ),
    path(
        "remove-cart-item/<cart_item_id>/",
        views.remove_cart_item,
        name="remove_cart_item",
    ),
    path(
        "remove-favourite-item/<favourite_item_id>/",
        views.remove_favourite_item,
        name="remove_favourite_item",
    ),
    path("checkout", views.checkout, name="checkout"),
    path("new_address", views.new_address, name="new_address"),
    path("edit-address/<address_id>/", views.edit_address, name="edit_address"),
    path("remove-address/<address_id>/", views.remove_address, name="remove_address"),
    path(
        "default-address/<address_id>/", views.default_address, name="default_address"
    ),
    path("place_order", views.place_order, name="place_order"),
    path("cancel-order/<order_id>/", views.cancel_order, name="cancel_order"),
    path(
        "cancel-order-item/<order_item_id>/",
        views.cancel_order_item,
        name="cancel_order_item",
    ),
    path("wallet", views.customer_wallet, name="customer_wallet"),
    path("invoice/<order_id>/", views.invoice, name="invoice"),
]