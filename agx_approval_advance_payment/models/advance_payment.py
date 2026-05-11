from odoo import _, api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    approval_request_count = fields.Integer(
        compute="_compute_approval_request_count",
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        req_id = self.env.context.get("default_approval_request_id")
        if req_id and "analytic_distribution" in fields_list:
            req = self.env["approval.request"].browse(req_id)
            if req.analytic_distribution:
                defaults["analytic_distribution"] = req.analytic_distribution
        return defaults

    @api.depends("approval_request_id")
    def _compute_approval_request_count(self):
        for rec in self:
            rec.approval_request_count = 1 if rec.approval_request_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            req = rec.approval_request_id
            if req and not req.advance_payment_id:
                req.advance_payment_id = rec.id
                req.message_post(
                    body=_(
                        "สร้างสัญญายืมเงิน"
                        " <a href='/web#id=%(id)s&amp;model=advance.payment'>"
                        "<b>%(name)s</b></a> แล้ว"
                        " จำนวน <b>%(amount)s %(currency)s</b>",
                        id=rec.id,
                        name=rec.name,
                        amount=rec.loan_amount,
                        currency=rec.currency_id.name,
                    ),
                    message_type="comment",
                )
        return records

    def action_view_approval_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
