from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AdvancePaymentReturn(models.Model):
    _name = "advance.payment.return"
    _description = "Advance Payment Return"
    _inherit = ["mail.thread"]
    _order = "date_return desc"

    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
        required=True,
        ondelete="cascade",
    )
    date_return = fields.Date(string="Return Date", tracking=True)
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        tracking=True,
    )
    note = fields.Text(string="Note")
    return_type = fields.Selection(
        [
            ("expense", "ใบเสร็จ"),
            ("refund", "คืนเงิน"),
        ],
        string="Return Type",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("submitted", "Submitted"),
            ("validated", "Validated"),
            ("done", "Done"),
        ],
        default="submitted",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        string="Attachments",
    )
    date_submitted = fields.Date(string="Submitted Date", readonly=True)
    date_validated = fields.Date(string="Validated Date", readonly=True)
    date_done = fields.Date(string="Done Date", readonly=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="advance_payment_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="advance_payment_id.company_id",
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "date_submitted" not in vals:
                vals["date_submitted"] = fields.Date.today()
        return super().create(vals_list)

    def action_validate(self):
        self._check_officer()
        for rec in self:
            rec.write({"state": "validated", "date_validated": fields.Date.today()})
            rec.advance_payment_id._check_fully_returned()

    def action_done(self):
        self._check_officer()
        for rec in self:
            rec.write({"state": "done", "date_done": fields.Date.today()})
            rec.advance_payment_id._check_fully_returned()

    def _check_officer(self):
        if not self.env.user.has_group(
            "advance_payment.group_advance_payment_officer"
        ):
            raise UserError(_("Only officers can perform this action."))
