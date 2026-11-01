# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError

PAPER_IMPORT_GROUP = "disbursement_paper_import.group_disbursement_paper_import"


class DisbursementRequest(models.Model):
    """Marks a request that was keyed in from a paper form. Only the paper
    import group may set or clear the flag; the view enforces it for the UI and
    create/write for RPC."""

    _inherit = "disbursement.request"

    is_paper_import = fields.Boolean(
        string="Imported from Paper",
        copy=False,
        tracking=True,
        help="This request was keyed in from a paper disbursement form.",
    )

    def _check_paper_import_access(self):
        if not self.env.su and not self.env.user.has_group(PAPER_IMPORT_GROUP):
            raise AccessError(
                _("Only the Disbursement Paper Import group can flag requests.")
            )

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("is_paper_import") for vals in vals_list):
            self._check_paper_import_access()
        return super().create(vals_list)

    def write(self, vals):
        if "is_paper_import" in vals:
            self._check_paper_import_access()
        return super().write(vals)
