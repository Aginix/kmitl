import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Transfer all ir.model.data ownership from l10n_th_gov_purchase_request
    to purchase_request_kmitl after module merge."""
    _logger.info(
        "Transferring ir.model.data from merged modules to purchase_request_kmitl"
    )
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = 'purchase_request_kmitl'
        WHERE module IN (
            'l10n_th_gov_purchase_request',
            'procurement_method_no_security',
            'procurement_type_no_security'
        )
        """
    )
    cr.execute(
        """
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name IN (
            'l10n_th_gov_purchase_request',
            'procurement_method_no_security',
            'procurement_type_no_security'
        )
        """
    )
