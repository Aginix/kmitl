from odoo import api, fields, models


class AdvancePaymentLoanType(models.Model):
    _inherit = "advance.payment.loan.type"

    group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="กลุ่มที่เลือกได้",
        help="ถ้าระบุ เฉพาะสมาชิกของกลุ่มเหล่านี้เลือกประเภทนี้ตอนร่างคำขอได้ ถ้าว่างไว้ ทุกคนเลือกได้",
    )
    is_selectable = fields.Boolean(
        compute="_compute_is_selectable",
        search="_search_is_selectable",
        help="Whether the current user may choose this type when drafting.",
    )

    @api.depends("group_ids")
    @api.depends_context("uid")
    def _compute_is_selectable(self):
        user_groups = self.env.user.groups_id
        for rec in self:
            rec.is_selectable = not rec.group_ids or bool(rec.group_ids & user_groups)

    def _search_is_selectable(self, operator, value):
        selectable = [
            "|",
            ("group_ids", "=", False),
            ("group_ids", "in", self.env.user.groups_id.ids),
        ]
        if (operator == "=") == bool(value):
            return selectable
        return ["!"] + selectable
