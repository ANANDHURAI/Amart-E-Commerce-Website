from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('shop/', views.shop, name='shop'),
    path('product/<slug>/', views.product_page, name='product_page'),
    path('test-modal/', views.test_modal_view, name='test_modal'),
]