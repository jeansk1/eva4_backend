# core/context_processors.py
def user_info(request):
    """
    Context processor para pasar información del usuario a los templates
    """
    if request.user.is_authenticated:
        return {
            'user_role': request.user.rol,
            'user_compania': request.user.compania,
            'is_admin_cliente': request.user.rol == 'admin_cliente',
            'is_gerente': request.user.rol == 'gerente',
            'is_vendedor': request.user.rol == 'vendedor',
            'is_super_admin': request.user.rol == 'super_admin',
        }
    return {}