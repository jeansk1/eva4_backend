# config/urls.py - VERSIÓN FINAL COMPLETA
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # --- ADMINISTRACIÓN Y API ---
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    
    # --- VISTAS PRINCIPALES ---
    path('', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),

    # --- MÓDULO PRODUCTOS ---
    path('productos/', TemplateView.as_view(template_name='productos/list.html'), name='productos_list'),
    path('productos/create/', TemplateView.as_view(template_name='productos/create.html'), name='productos_create'),
    path('productos/detalle/', TemplateView.as_view(template_name='productos/detail.html'), name='productos_detail'),
    path('productos/edit/', TemplateView.as_view(template_name='productos/edit.html'), name='productos_edit'), # Faltaba esta

    # --- MÓDULO INVENTARIO ---
    path('inventario/', TemplateView.as_view(template_name='inventario/list.html'), name='inventario_list'),
    path('inventario/ajustar/', TemplateView.as_view(template_name='inventario/ajustar.html'), name='inventario_ajustar'),
    path('inventario/movimientos/', TemplateView.as_view(template_name='inventario/movimientos.html'), name='inventario_movimientos'),

    # --- MÓDULO VENTAS (POS) ---
    path('ventas/', TemplateView.as_view(template_name='ventas/nueva.html'), name='ventas_pos'),
    path('ventas/dashboard/', TemplateView.as_view(template_name='ventas/dashboard.html'), name='ventas_dashboard'),
    path('ventas/historial/', TemplateView.as_view(template_name='ventas/historial.html'), name='ventas_historial'),
    path('ventas/recibo/', TemplateView.as_view(template_name='ventas/recibo.html'), name='ventas_recibo'), # Faltaba esta
    path('ventas/ordenes/', TemplateView.as_view(template_name='ventas/ordenes.html'), name='ventas-ordenes-web'),

    # --- MÓDULO PROVEEDORES ---
    path('proveedores/', TemplateView.as_view(template_name='proveedores/list.html'), name='proveedores_list'),
    path('proveedores/create/', TemplateView.as_view(template_name='proveedores/create.html'), name='proveedores_create'), # Faltaba esta
    path('proveedores/detalle/', TemplateView.as_view(template_name='proveedores/detail.html'), name='proveedores_detail'),

    # --- MÓDULO SUCURSALES ---
    path('sucursales/', TemplateView.as_view(template_name='sucursales/list.html'), name='sucursales_list'),
    path('sucursales/create/', TemplateView.as_view(template_name='sucursales/create.html'), name='sucursales_create'), # Faltaba esta
    path('sucursales/detail/', TemplateView.as_view(template_name='sucursales/detail.html'), name='sucursales_detail'),
    path('sucursales/edit/', TemplateView.as_view(template_name='sucursales/edit.html'), name='sucursales_edit'),

    # --- MÓDULO USUARIOS ---
    path('usuarios/', TemplateView.as_view(template_name='usuarios/list.html'), name='usuarios_list'),
    path('usuarios/crear/', TemplateView.as_view(template_name='usuarios/crear.html'), name='usuarios_create'), # Faltaba esta
    path('usuarios/perfil/', TemplateView.as_view(template_name='usuarios/perfil.html'), name='usuarios_perfil'), # Faltaba esta
    path('usuarios/<int:id>/', TemplateView.as_view(template_name='usuarios/detail.html'), name='usuarios_detail'),

    # --- TIENDA E-COMMERCE (PÚBLICA) ---
    # Nota: Si usas 'include(shop.urls)', asegúrate de que shop/urls.py tenga estas rutas.
    # Si no, defínelas aquí directamente para asegurar que funcionen con los templates que hicimos:
    path('tienda/', TemplateView.as_view(template_name='tienda/catalogo.html'), name='tienda_home'),
    path('tienda/carrito/', TemplateView.as_view(template_name='tienda/carrito.html'), name='tienda_carrito'),
    path('tienda/pago/', TemplateView.as_view(template_name='tienda/pago.html'), name='tienda_pago'),
    path('tienda/confirmacion/', TemplateView.as_view(template_name='tienda/confirmacion.html'), name='tienda_confirmacion'),
    path('tienda/producto/<int:id>/', TemplateView.as_view(template_name='tienda/producto_detalle.html'), name='tienda_producto_detail'), # Faltaba esta
    

    # --- REPORTES AVANZADOS ---
    # Lo mismo aquí, definimos las rutas directas para los templates específicos
    path('reportes/', TemplateView.as_view(template_name='reportes/dashboard.html'), name='reportes_dashboard'),
    path('reportes/stock/', TemplateView.as_view(template_name='reportes/stock.html'), name='reportes_stock'), # Faltaba esta
    path('reportes/ventas/', TemplateView.as_view(template_name='reportes/ventas.html'), name='reportes_ventas'), # Faltaba esta
    path('reportes/proveedores/', TemplateView.as_view(template_name='reportes/proveedores.html'), name='reportes_proveedores'), # Faltaba esta
]

# Configuración para archivos estáticos y media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)