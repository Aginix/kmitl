from odoo import api, fields, models

READER_RULE = (
    "agx_approval_disbursement_operating_unit.approval_request_disbursement_reader_rule"
)


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # Whoever may read a ใบขอเบิก may read the request it references, so a
    # reviewer in another unit sees what was approved (agx_approval ADR-0010).
    # The reader groups are the groups of READER_RULE (one list, in its XML).
    shared_group_ids = fields.Many2many(
        compute="_compute_shared_group_ids",
        store=True,
    )

    @api.depends("disbursement_request_ids")
    def _compute_shared_group_ids(self):
        rule = self.env.ref(READER_RULE, raise_if_not_found=False)
        readers = rule.sudo().groups if rule else self.env["res.groups"]
        for record in self:
            record.shared_group_ids = (
                readers if record.sudo().disbursement_request_ids else False
            )
