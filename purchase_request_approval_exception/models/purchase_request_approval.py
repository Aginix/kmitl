from odoo import api, models


class PurchaseRequestApproval(models.Model):
    """Wire the OCA ``base.exception`` framework onto ``purchase.request.approval``.

    The ส่งเข้าสารบรรณ hook (``action_submit_to_sarabun``) runs the review popup
    on blocking exceptions and clears exception state when the สารบรรณ document
    is returned or cancelled so a fresh re-submit re-earns its confirmation. The
    Vendor-required check that used to live in ``_sarabun_submit_guard`` is now
    the configurable ``purchase_request_approval_excep_partner_required`` rule.
    """

    _name = "purchase.request.approval"
    _inherit = ["purchase.request.approval", "base.exception"]
    # Keep the พจ.1's own ordering — mixing in base.exception would otherwise
    # pull its "main_exception_id asc" _order.
    _order = "date_start desc, name desc"

    @api.model
    def _reverse_field(self):
        return "purchase_request_approval_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "purchase_request_approval_exception"
            ".action_purchase_request_approval_exception_confirm"
        )

    def action_submit_to_sarabun(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_submit_to_sarabun()

    def _on_sarabun_returned(self, document, step):
        self.exception_ids = False
        self.main_exception_id = False
        self.ignore_exception = False
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_cancelled(self, document):
        self.exception_ids = False
        self.main_exception_id = False
        self.ignore_exception = False
        return super()._on_sarabun_cancelled(document)

    def purchase_request_approval_check_partner_required(self):
        # base.exception (by_method): return the records that FAIL the rule.
        return self.filtered(lambda r: not r.partner_id)
