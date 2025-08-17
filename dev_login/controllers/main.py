import logging
import werkzeug

from odoo import http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class DevLoginController(http.Controller):

    @http.route('/dev_login/admin', type='http', auth='none', methods=['POST'], csrf=False)
    def dev_login_admin(self, **kwargs):
        """
        Quick admin login endpoint for development and runbot environments.
        Provides convenient admin access for testing and development.
        """
        
        try:
            # Find admin user (usually user ID 2, but let's be safe)
            admin_user = request.env['res.users'].sudo().search([
                ('login', '=', 'admin')
            ], limit=1)
            
            if not admin_user:
                # Fallback to superuser
                admin_user = request.env['res.users'].sudo().browse(1)
            
            if admin_user:
                # Perform login
                request.session.authenticate(request.session.db, admin_user.login, 'admin')
                _logger.info(f"Admin login successful for user: {admin_user.login}")
                
                # Redirect to web client
                return werkzeug.utils.redirect('/web')
            else:
                _logger.error("No admin user found for dev login")
                return werkzeug.exceptions.NotFound("Admin user not found")
                
        except Exception as e:
            _logger.error(f"Dev login failed: {str(e)}")
            return werkzeug.exceptions.InternalServerError("Login failed")