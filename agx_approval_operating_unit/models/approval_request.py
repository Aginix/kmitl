from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        tracking=True,
    )

    # Further groups whose members may read this request (and its lines,
    # participants, attachments) whatever their operating unit — read-only,
    # through the OU record rules. Empty here; a bridge fills it, e.g. with the
    # groups that read the ใบขอเบิก referencing it (agx_approval ADR-0010).
    shared_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="approval_request_shared_group_rel",
        column1="request_id",
        column2="group_id",
        string="Shared with Groups",
        readonly=True,
        copy=False,
    )

    def _get_budget_commitment_extra_kwargs(self):
        vals = super()._get_budget_commitment_extra_kwargs()
        if self.operating_unit_id:
            vals["operating_unit_id"] = self.operating_unit_id.id
        return vals
