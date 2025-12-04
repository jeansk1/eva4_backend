import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import *
from django.contrib.auth import get_user_model

Usuario = get_user_model()

def crear_datos_iniciales():
    # Crear compañía
    compania, _ = Compania.objects.get_or_create(
        nombre="Tienda Ejemplo SA",
        defaults={
            'rut': '76.543.210-9',
            'direccion': 'Calle Falsa 123, Temuco',
            'telefono': '+56912345678',
            'email': 'contacto@tiendaejemplo.cl'
        }
    )
    
    # Crear super admin
    super_admin, _ = Usuario.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@temucosoft.cl',
            'rut': '12.345.678-9',
            'rol': 'super_admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    super_admin.set_password('admin123')
    super_admin.save()
    
    # Crear sucursal
    sucursal, _ = Sucursal.objects.get_or_create(
        nombre="Sucursal Central",
        compania=compania,
        defaults={
            'direccion': 'Av. Principal 456, Temuco',
            'telefono': '+56987654321',
            'email': 'central@tiendaejemplo.cl'
        }
    )
    
    # Crear usuario admin cliente
    admin_cliente, _ = Usuario.objects.get_or_create(
        username='admincliente',
        defaults={
            'email': 'admin@tiendaejemplo.cl',
            'rut': '98.765.432-1',
            'rol': 'admin_cliente',
            'compania': compania
        }
    )
    admin_cliente.set_password('cliente123')
    admin_cliente.save()
    
    print("✅ Datos iniciales creados exitosamente!")
    print(f"   Super Admin: admin / admin123")
    print(f"   Admin Cliente: admincliente / cliente123")

if __name__ == "__main__":
    crear_datos_iniciales()