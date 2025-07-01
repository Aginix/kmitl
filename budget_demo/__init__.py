# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import demo


def post_init_hook(cr, registry):
    """Generate demo data after module installation"""
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    _logger.info("Budget demo module: Running post_init_hook")
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        # Generate demo budget moves
        demo_generator = env['budget.demo']
        result = demo_generator.generate_demo_data()
        
        if result:
            _logger.info("Budget demo data generated successfully")
        else:
            _logger.warning("Budget demo data generation skipped or failed")
            
    except Exception as e:
        _logger.error(f"Error in budget demo post_init_hook: {str(e)}")


def post_load_hook(cr, registry):
    """Generate demo data after module upgrade/reload"""
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    _logger.info("Budget demo module: Running post_load_hook")
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        # Generate demo budget moves (will skip if already exists)
        demo_generator = env['budget.demo']
        result = demo_generator.generate_demo_data()
        
        if result:
            _logger.info("Budget demo data generated successfully during upgrade")
        else:
            _logger.info("Budget demo data already exists or generation skipped")
            
    except Exception as e:
        _logger.error(f"Error in budget demo post_load_hook: {str(e)}")


def uninstall_hook(cr, registry):
    """Clean up demo data when module is uninstalled"""
    import logging
    from odoo import api, SUPERUSER_ID
    
    _logger = logging.getLogger(__name__)
    _logger.info("Budget demo module: Running uninstall_hook")
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        # Remove demo budget moves
        demo_generator = env['budget.demo']
        result = demo_generator.remove_demo_data()
        
        if result:
            _logger.info("Budget demo data removed successfully")
        else:
            _logger.warning("Budget demo data removal failed")
            
    except Exception as e:
        _logger.error(f"Error in budget demo uninstall_hook: {str(e)}")
