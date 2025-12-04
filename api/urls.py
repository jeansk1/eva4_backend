# api/urls.py - 
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import views  # ← Solo esta importación
from .views import CustomTokenObtainPairView, DiagnosticoPlanView, DashboardView

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
    
    #--- DIAGNÓSTICO DE PLAN ---
    path('diagnostico/plan/', views.DiagnosticoPlanView.as_view(), name='diagnostico-plan'),

    #--- DASHBOARD STATS ---
    path('dashboard/stats/', DashboardView.as_view(), name='dashboard-stats'),
    
    # Rutas personalizadas para el carrito de compras
    path('carrito/checkout/', views.ItemCarritoViewSet.as_view({'post': 'checkout'}), name='carrito-checkout'),
    
    # Nueva ruta para fusionar carritos
    path('carrito/fusionar/', views.FusionarCarritoView.as_view(), name='carrito-fusionar'),
    

    # 2. RUTAS GENÉRICAS DEL ROUTER (Van al FINAL)
    path('', include(router.urls)),
]