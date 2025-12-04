import requests
import json
import random
from datetime import datetime

# --- CONFIGURACIÓN ---
BASE_URL = 'http://127.0.0.1:8000/api'
# ¡IMPORTANTE! Usa las credenciales del Superusuario que creaste
USERNAME = 'jean'      # Cambia esto si tu usuario es diferente
PASSWORD = 'admin123'   # Cambia esto por tu contraseña real

# Colores para la terminal
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'

def log(msg, success=True):
    color = GREEN if success else RED
    print(f"{color}[{'OK' if success else 'ERROR'}] {msg}{RESET}")

def get_token():
    print("1. Iniciando sesión...")
    url = f"{BASE_URL}/auth/login/"
    try:
        response = requests.post(url, json={'username': USERNAME, 'password': PASSWORD})
        if response.status_code == 200:
            token = response.json()['access']
            # Capturamos datos extra del usuario para validaciones
            user_data = response.json() 
            log(f"Login exitoso. Usuario: {user_data.get('username')}")
            return token, user_data
        else:
            log(f"Fallo login: {response.text}", False)
            exit()
    except Exception as e:
        log(f"No se pudo conectar al servidor. ¿Está corriendo? ({e})", False)
        exit()

def create_company(headers):
    print("\n2. Creando Compañía...")
    url = f"{BASE_URL}/companias/"
    data = {
        "nombre": "TecnoSur Limitada",
        "rut": "76456789-7",
        "direccion": "Av. Alemania 0150, Temuco",
        "telefono": "+56912345678",
        "email": "contacto@tecnosur.cl"
    }
    # Verificamos si ya existe para no duplicar (simple check)
    res = requests.get(url, headers=headers)
    if res.ok and len(res.json()) > 0:
        log("Compañía ya existía, usando la primera encontrada.")
        return res.json()[0]['id']

    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 201:
        data = res.json()
        log(f"Compañía creada: {data['nombre']} (ID: {data['id']})")
        return data['id']
    else:
        log(f"Error creando compañía: {res.text}", False)
        exit()

def assign_company_to_user(headers, company_id, user_data):
    # Si el usuario es superadmin y no tiene compañía, se la asignamos para que los filtros funcionen
    print(f"\n2.5. Asignando compañía al usuario {user_data['username']}...")
    if not user_data.get('compania_id'):
        user_id = 1 # Asumimos ID 1 para superusuario, o podrías sacar ID del token decode
        # Nota: La API de usuarios requiere ID. Si tu login no devuelve ID, esto podría fallar.
        # Intentaremos actualizar el usuario actual.
        url = f"{BASE_URL}/usuarios/me/"
        res_me = requests.get(url, headers=headers)
        if res_me.ok:
            my_id = res_me.json()['id']
            url_update = f"{BASE_URL}/usuarios/{my_id}/"
            requests.patch(url_update, json={'compania': company_id}, headers=headers)
            log("Compañía asignada al usuario actual.")

def create_branch(headers, company_id):
    print("\n3. Creando Sucursal...")
    url = f"{BASE_URL}/sucursales/"
    data = {
        "nombre": "Casa Matriz",
        "compania": company_id,
        "direccion": "Calle Manuel Montt 850",
        "telefono": "452232323",
        "email": "matriz@tecnosur.cl"
    }
    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 201:
        d = res.json()
        log(f"Sucursal creada: {d['nombre']} (ID: {d['id']})")
        return d['id']
    else:
        log(f"Error creando sucursal (quizás ya existe?): {res.text}", False)
        # Intentar obtener existente
        res_get = requests.get(url, headers=headers)
        if res_get.ok and len(res_get.json()) > 0:
            return res_get.json()[0]['id']
        exit()

def create_provider(headers, company_id):
    print("\n4. Creando Proveedor...")
    url = f"{BASE_URL}/proveedores/"
    data = {
        "nombre": "Ingram Micro Chile",
        "rut": "96789123-1",
        "compania": company_id,
        "contacto": "Roberto Ventas",
        "telefono": "+5622334455",
        "email": "ventas@ingram.cl",
        "direccion": "El Rosal 456, Huechuraba"
    }
    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 201:
        d = res.json()
        log(f"Proveedor creado: {d['nombre']} (ID: {d['id']})")
        return d['id']
    return 1 # Fallback

def create_products(headers, company_id):
    print("\n5. Creando Productos...")
    url = f"{BASE_URL}/productos/"
    products_data = [
        {
            "sku": f"MS-LOG-{random.randint(100,999)}",
            "nombre": "Mouse Gamer Logitech G203",
            "descripcion": "Mouse RGB 8000 DPI",
            "precio": 24990,
            "costo": 15000,
            "categoria": "electronica",
            "compania": company_id
        },
        {
            "sku": f"CC-ZER-{random.randint(100,999)}",
            "nombre": "Bebida Cola Zero 3L",
            "descripcion": "Formato familiar",
            "precio": 3200,
            "costo": 1800,
            "categoria": "bebidas",
            "compania": company_id
        }
    ]
    created_ids = []
    for p in products_data:
        res = requests.post(url, json=p, headers=headers)
        if res.status_code == 201:
            d = res.json()
            log(f"Producto creado: {d['nombre']} - Precio: ${d['precio']}")
            created_ids.append(d['id'])
        else:
            log(f"Error producto: {res.text}", False)
    return created_ids

def create_purchase(headers, branch_id, provider_id, product_ids):
    print("\n6. Registrando COMPRA (Ingreso de Stock)...")
    if not product_ids:
        log("No hay productos para comprar", False)
        return

    url = f"{BASE_URL}/compras/"
    
    # Compramos 100 unidades del primer producto y 50 del segundo
    items = []
    items.append({"producto": product_ids[0], "cantidad": 100, "precio_unitario": 15000})
    if len(product_ids) > 1:
        items.append({"producto": product_ids[1], "cantidad": 50, "precio_unitario": 1800})

    data = {
        "sucursal": branch_id,
        "proveedor": provider_id,
        "numero_factura": f"FE-{random.randint(1000,9999)}",
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "items": items
    }

    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 201:
        d = res.json()
        log(f"Compra registrada exitosamente! Factura: {d['numero_factura']}")
        log(f"Stock aumentado automáticamente. Total Compra: ${d['total']}")
    else:
        log(f"Error en compra: {res.text}", False)

def create_sale(headers, branch_id, product_ids):
    print("\n7. Registrando VENTA (Salida de Stock - POS)...")
    if not product_ids: return

    url = f"{BASE_URL}/ventas/"
    
    # Vendemos 5 unidades del primer producto
    items = [
        {"producto": product_ids[0], "cantidad": 5}
    ]

    data = {
        "sucursal": branch_id,
        "metodo_pago": "debito",
        "items": items
    }

    res = requests.post(url, json=data, headers=headers)
    if res.status_code == 201:
        d = res.json()
        log(f"Venta POS registrada! ID: {d['id']}")
        log(f"Stock descontado. Total Venta: ${d['total']}")
    else:
        log(f"Error en venta: {res.text}", False)

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    print("--- INICIANDO CARGA DE DATOS AUTOMÁTICA ---")
    
    # 1. Login
    token, user_data = get_token()
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Estructura Organizacional
    company_id = create_company(headers)
    assign_company_to_user(headers, company_id, user_data)
    
    branch_id = create_branch(headers, company_id)
    provider_id = create_provider(headers, company_id)

    # 3. Productos
    prod_ids = create_products(headers, company_id)

    # 4. Movimientos (Prueba de fuego del Backend)
    create_purchase(headers, branch_id, provider_id, prod_ids) # Suma stock
    create_sale(headers, branch_id, prod_ids)                  # Resta stock

    print("\n--- CARGA FINALIZADA EXITOSAMENTE ---")
    print("Ahora ve a http://127.0.0.1:8000/ y revisa el Dashboard.")