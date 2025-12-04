# core/middleware.py - CREA ESTE ARCHIVO
from django.utils.deprecation import MiddlewareMixin

class ForceSessionMiddleware(MiddlewareMixin):
    """
    Middleware que asegura que TODOS los usuarios (incluidos anónimos) 
    tengan una sesión activa
    """
    
    def process_request(self, request):
        # Verificar si ya tiene sesión
        if not request.session.session_key:
            # Crear nueva sesión
            request.session.create()
            print(f"🔧 FORCE SESSION: Nueva sesión creada para usuario anónimo")
            print(f"🔧 Session key: {request.session.session_key}")
        
        # DEBUG: Ver información de la sesión
        print(f"🔧 SESSION INFO - Key: {request.session.session_key}")
        print(f"🔧 SESSION INFO - User: {request.user}")
        print(f"🔧 SESSION INFO - Authenticated: {request.user.is_authenticated}")
        
        return None