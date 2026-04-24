from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('products/', views.products, name='products'),
    path('products/delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('categories/', views.categories, name='categories'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    path('orders/', views.orders, name='orders'),
    path('orders/delete/<int:pk>/', views.delete_order, name='delete_order'),
    path('suppliers/', views.suppliers, name='suppliers'),
    path('suppliers/delete/<int:pk>/', views.delete_supplier, name='delete_supplier'),
]
