def migrate(cr, version):
    """Transfer ir_model_data ownership of sarabun records to the new
    purchase_request_approval_sarabun module so Odoo does not delete them
    during the upgrade of purchase_request_approval, and so the new module
    can find and update them by their XML IDs on install.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'purchase_request_approval_sarabun'
         WHERE module = 'purchase_request_approval'
           AND name IN (
               'position_pa_approver',
               'route_template_purchase_request_approval',
               'route_template_line_pa_approve',
               'document_type_purchase_request_approval',
               'action_report_sarabun_document_purchase_request_approval',
               'report_sarabun_document_purchase_request_approval',
               'report_purchase_request_approval_sarabun_endorsement',
               'view_purchase_request_approval_return_cancel_wizard_form',
               'access_purchase_request_approval_return_cancel_wizard_user'
           )
        """
    )
