# TemucoSoft - Sistema de Gestión POS & E-commerce

Sistema integral de gestión para pymes minoristas desarrollado con **Django REST Framework**. Incluye Punto de Venta (POS), E-commerce público, gestión de inventario, proveedores y reportes gerenciales con control de acceso basado en roles (RBAC).

## 🚀 Características Principales

* **Autenticación Segura:** Login mediante **JWT** (JSON Web Tokens) con rotación de refresh tokens.
* **Gestión de Roles:** Perfiles diferenciados para Super Admin, Admin Cliente, Gerente y Vendedor con permisos granulares.
* **Inventario Inteligente:**
    * Control de stock atómico (evita ventas sin stock real).
    * Ingreso de mercadería mediante Compras a Proveedores.
    * Ajustes manuales y semáforo de stock (Crítico/Bajo/Ok).
* **Punto de Venta (POS):** Interfaz rápida para cajeros con buscador, carrito y emisión de recibos térmicos.
* **E-commerce:** Catálogo público, carrito de compras persistente y checkout para clientes finales.
* **Reportes y KPIs:** Dashboards visuales con gráficos (Chart.js) para ventas diarias, valorización de inventario y rendimiento.
* **Validaciones:** Algoritmo de RUT chileno (Módulo 11), validación de precios y fechas lógicas.

## 🛠️ Tecnologías

* **Backend:** Python 3.11+, Django 5.x, Django REST Framework.
* **Frontend:** HTML5, Bootstrap 5, JavaScript (Fetch API).
* **Base de Datos:** SQLite (Desarrollo) / PostgreSQL (Producción/AWS).
* **Infraestructura:** Gunicorn, Nginx (Configuración lista para EC2).

---

## ⚙️ Guía de Instalación (Local)

Sigue estos pasos para levantar el proyecto desde cero:

### 1. Clonar y preparar entorno
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Instalar dependencias
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers requests
# O si existe requirements.txt: pip install -r requirements.txt