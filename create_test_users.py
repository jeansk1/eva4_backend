import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User, Company
from django.contrib.auth import get_user_model

User = get_user_model()

def create_test_users():
    # Crear compañía de prueba si no existe
    company, created = Company.objects.get_or_create(
        name="Mi Tienda Test",
        defaults={
            'rut': '76.543.210-1',
            'address': 'Av. Test 123, Temuco',
            'phone': '+56912345678',
            'email': 'test@mitienda.cl'
        }
    )
    
    # Crear usuarios de prueba si no existen
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@temucosoft.cl',
            'password': 'Admin123',
            'rut': '12.345.678-9',
            'role': 'super_admin',
            'company': company
        },
        {
            'username': 'vendedor',
            'email': 'vendedor@mitienda.cl',
            'password': 'Vendedor123',
            'rut': '11.223.344-5',
            'role': 'vendedor',
            'company': company
        },
        {
            'username': 'gerente',
            'email': 'gerente@mitienda.cl',
            'password': 'Gerente123',
            'rut': '22.334.455-6',
            'role': 'gerente',
            'company': company
        },
        {
            'username': 'admin_cliente',
            'email': 'dueno@mitienda.cl',
            'password': 'AdminCliente123',
            'rut': '33.445.566-7',
            'role': 'admin_cliente',
            'company': company
        }
    ]
    
    for user_data in users_data:
        if not User.objects.filter(username=user_data['username']).exists():
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                rut=user_data['rut'],
                role=user_data['role'],
                company=user_data['company']
            )
            print(f"✅ Usuario creado: {user.username} ({user.role})")
        else:
            print(f"⚠️ Usuario ya existe: {user_data['username']}")

if __name__ == "__main__":
    create_test_users()