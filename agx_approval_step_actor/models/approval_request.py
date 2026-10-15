from odoo import api, fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    step_actor_ids = fields.Many2many(
        "res.users",
        string="ผู้มีสิทธิ์ดำเนินการ",
        compute="_compute_step_actor_ids",
    )

    def _get_step_actor_groups(self):
        """Map each state to the group that may act there; extension hook."""
        return {
            "to_verify": "agx_approval.group_approval_verify",
            "to_commit": "agx_approval.group_approval_budget_commit",
        }

    @api.depends("state", "operating_unit_id")
    def _compute_step_actor_ids(self):
        groups = self._get_step_actor_groups()
        for rec in self:
            xmlid = groups.get(rec.state)
            group = xmlid and self.env.ref(xmlid, raise_if_not_found=False)
            if not group or not rec.operating_unit_id:
                rec.step_actor_ids = False
                continue
            # sudo: regular users cannot read group membership or OU users
            rec.step_actor_ids = (
                group.sudo().users & rec.operating_unit_id.sudo().user_ids
            ).filtered(lambda u: not u.share)
