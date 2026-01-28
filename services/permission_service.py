
from models.entities import RolUsuario

class PermissionService:
    # Permissions definition
    CAN_VIEW_DASHBOARD = "view_dashboard"
    CAN_VIEW_VENCIMIENTOS = "view_vencimientos"
    CAN_EDIT_VENCIMIENTOS = "edit_vencimientos" # Create/Update/Pay
    CAN_DELETE_VENCIMIENTOS = "delete_vencimientos"
    
    CAN_MANAGE_USERS = "manage_users"
    CAN_MANAGE_CONFIG = "manage_config" # DB Admin, Settings
    CAN_MANAGE_CATALOGS = "manage_catalogs" # Create/Edit Inmuebles, Proveedores
    
    CAN_VIEW_REPORTS = "view_reports"
    
    # Role -> Permissions Mapping
    ROLE_PERMISSIONS = {
        RolUsuario.ADMIN: {
            CAN_VIEW_DASHBOARD, 
            CAN_VIEW_VENCIMIENTOS, CAN_EDIT_VENCIMIENTOS, CAN_DELETE_VENCIMIENTOS,
            CAN_MANAGE_USERS, CAN_MANAGE_CONFIG, CAN_MANAGE_CATALOGS,
            CAN_VIEW_REPORTS
        },
        RolUsuario.OPERADOR: {
            CAN_VIEW_DASHBOARD,
            CAN_VIEW_VENCIMIENTOS, CAN_EDIT_VENCIMIENTOS,
            CAN_MANAGE_CATALOGS, # Operador can create providers/inmuebles needed for daily work
            CAN_VIEW_REPORTS
        },
        RolUsuario.INVITADO: { # LECTURA
            CAN_VIEW_DASHBOARD,
            CAN_VIEW_VENCIMIENTOS,
            CAN_VIEW_REPORTS
            # NO Edit, NO Delete, NO Users, NO Catalogs Edit (View only implication in views)
        }
    }

    @staticmethod
    def user_has_permission(user, permission):
        if not user or not user.rol:
            return False
            
        # Handle string roles if they come as strings (though model should give enum now)
        role_enum = user.rol
        if isinstance(role_enum, str):
            # Try to match string to Enum
            try:
                role_enum = next((r for r in RolUsuario if r.value == role_enum), None)
            except:
                pass
                
        if not role_enum:
            return False
            
        perms = PermissionService.ROLE_PERMISSIONS.get(role_enum, set())
        return permission in perms

    @staticmethod
    def is_admin(user):
        return PermissionService.user_has_permission(user, PermissionService.CAN_MANAGE_USERS)
