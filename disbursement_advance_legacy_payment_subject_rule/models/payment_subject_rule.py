from odoo import fields, models


class DisbursementPaymentSubjectRule(models.Model):
    _inherit = "disbursement.payment.subject.rule"

    payment_type = fields.Selection(
        selection_add=[("advance_legacy", "เงินยืม (ระบบเก่า)")],
        ondelete={"advance_legacy": "cascade"},
    )
