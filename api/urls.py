# api/urls.py - CORREGIDO (Orden de rutas)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views
from .views import CustomTokenObtainPairView

router = DefaultRouter()
router.register(r'usuarios', views.UsuarioViewSet)
router.register(r'companias', views.CompaniaViewSet)
router.register(r'sucursales', views.SucursalViewSet)
router.register(r'productos', views.ProductoViewSet)
router.register(r'inventario', views.InventarioViewSet)
router.register(r'proveedores', views.ProveedorViewSet)
router.register(r'compras', views.CompraViewSet)
router.register(r'ventas', views.VentaViewSet)
router.register(r'ordenes', views.OrdenViewSet)
router.register(r'carrito', views.ItemCarritoViewSet, basename='carrito')

urlpatterns = [
    # 1. RUTAS ESPECÍFICAS (Deben ir PRIMERO)
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ESTA ES LA IMPORTANTE: Debe ir antes que router.urls
    path('usuarios/me/', views.UsuarioActualView.as_view(), name='usuario-actual'),
    
    path('reportes/', views.ReporteView.as_view(), name='reportes'),
    path('prueba/', views.VistaPruebaAPI.as_view(), name='api-prueba'),

    # 2. RUTAS GENÉRICAS DEL ROUTER (Van al FINAL)
    path('', include(router.urls)),
]