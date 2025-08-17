import logging
import werkzeug

from odoo import http, tools
from odoo.http import request

_logger = logging.getLogger(__name__)


class DevLoginController(http.Controller):

    @http.route('/dev_login/admin', type='http', auth='none', methods=['POST'], csrf=False)
    def dev_login_admin(self, **kwargs):
        """
        Quick admin login endpoint for development.
        Only works in development mode for security.
        """
        # Multiple security checks to prevent production use
        
        # Check 1: Only allow in development mode
        if not tools.config.get('dev_mode'):
            _logger.warning("Dev login attempted outside development mode from IP: %s", 
                          request.httprequest.environ.get('REMOTE_ADDR'))
            return werkzeug.exceptions.Forbidden("Not available in production")
        
        # Check 2: Verify debug mode is active
        if not request.session.debug:
            _logger.warning("Dev login attempted without debug mode from IP: %s", 
                          request.httprequest.environ.get('REMOTE_ADDR'))
            return werkzeug.exceptions.Forbidden("Debug mode required")
        
        # Check 3: Verify we're in a development database (optional additional check)
        db_name = request.session.db
        if db_name and any(prod_indicator in db_name.lower() 
                          for prod_indicator in ['production', 'prod', 'live']):
            _logger.warning("Dev login attempted on production-like database: %s", db_name)
            return werkzeug.exceptions.Forbidden("Not allowed on production database")
        
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
                _logger.info(f"Development admin login successful for user: {admin_user.login}")
                
                # Redirect to web client
                return werkzeug.utils.redirect('/web')
            else:
                _logger.error("No admin user found for dev login")
                return werkzeug.exceptions.NotFound("Admin user not found")
                
        except Exception as e:
            _logger.error(f"Dev login failed: {str(e)}")
            return werkzeug.exceptions.InternalServerError("Login failed")