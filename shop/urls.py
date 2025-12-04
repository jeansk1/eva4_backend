# shop/urls.py
from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='tienda/catalogo.html'), name='tienda-home'),
    path('carrito/', TemplateView.as_view(template_name='tienda/carrito.html'), name='carrito'),
    path('pago/', TemplateView.as_view(template_name='tienda/pago.html'), name='pago'),
]