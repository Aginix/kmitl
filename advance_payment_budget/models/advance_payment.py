from odoo import api, fields, models


class AdvancePayment(models.Model):
    """The budget side of a loan.

    Everything that ties a สัญญายืมเงิน to KMITL's financial dimensions and to
    งบประมาณ lives here, so the loan lifecycle in `advance_payment` stands on its
    own without the budget stack (ADR-0009): the analytic distribution the loan
    is charged to, the four dimension pickers derived from it, and the
    ใบจองงบประมาณ its cash is drawn against.
    """

    # _name is required alongside a multi-entry _inherit: Odoo only defaults it
    # to _inherit[0] when there is exactly one parent.
    _name = "advance.payment"
    _inherit = ["advance.payment", "analytic.mixin"]

    # Which earmark the borrowed cash comes out of. Copied off the source
    # document when the reference is picked, never reserved by the loan itself —
    # a loan creating its own commitment would double-reserve the same money
    # (agx_approval ADR-0003). A snapshot on purpose: the source is free to
    # release or re-point its own commitment afterwards without erasing the
    # record of where this cash came from. Empty for a standalone loan, whose
    # budget source is still an open policy question (ADR-0008).
    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="ใบจองงบประมาณ",
        readonly=True,
        copy=False,
        index=True,
        ondelete="restrict",
        tracking=True,
        help="ใบจองงบประมาณที่เงินยืมก้อนนี้เบิกออกมา "
        "คัดลอกมาจากเอกสารต้นทางตอนเลือกเอกสารอ้างอิง "
        "และใช้ส่งต่อให้ขั้นตัดงบประมาณ",
    )

    # Analytic dimension fields — computed from analytic_distribution, not stored
    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        compute="_compute_analytic_ids",
        inverse="_inverse_activity_analytic_id",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_ids",
        inverse="_inverse_department_analytic_id",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_ids",
        inverse="_inverse_fund_analytic_id",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_ids",
        inverse="_inverse_source_analytic_id",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_ids(self):
        for rec in self:
            values = {f: False for f in self._analytic_keys.values()}
            account_ids = [int(k) for k in (rec.analytic_distribution or {})]
            for account in self.env["account.analytic.account"].browse(account_ids):
                field = self._analytic_keys.get(account.plan_id.code)
                if field:
                    values[field] = account.id
            for field, val in values.items():
                rec[field] = val

    def _inverse_activity_analytic_id(self):
        self._update_analytic_distribution("activities")

    def _inverse_department_analytic_id(self):
        self._update_analytic_distribution("departments")

    def _inverse_fund_analytic_id(self):
        self._update_analytic_distribution("funds")

    def _inverse_source_analytic_id(self):
        self._update_analytic_distribution("sources")

    def _prepare_account_payment_vals(self, payment_type):
        """Charge the outbound payment to the same dimensions as the loan."""
        vals = super()._prepare_account_payment_vals(payment_type)
        vals["analytic_distribution"] = self.analytic_distribution
        return vals
