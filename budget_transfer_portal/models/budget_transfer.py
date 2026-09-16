from odoo import models


class BudgetTransfer(models.Model):
    """Expose ``budget.transfer`` on the customer portal.

    Adds ``portal.mixin`` so each transfer gets an ``access_url`` /
    ``access_token`` and can be opened at ``/my/budget-transfer/<id>`` with the
    งปม.303 PDF (from ``budget_transfer_pdf``) previewed inline.
    """

    _name = "budget.transfer"
    _inherit = ["budget.transfer", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for transfer in self:
            transfer.access_url = "/my/budget-transfer/%s" % transfer.id

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Budget Transfer-%s" % (self.name or self.id)
