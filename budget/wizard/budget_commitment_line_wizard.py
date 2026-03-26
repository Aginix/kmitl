from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetCommitmentLineWizard(models.TransientModel):
    """Wizard for adding commitment ledger lines (obligate/consume).

    Auto-fills account_id and analytic dimensions from the commitment header.
    User only needs to enter the amount and optional description.
    """

    _name = "budget.commitment.line.wizard"
    _description = "Add Commitment Line"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        readonly=True,
    )
    move_type = fields.Selection(
        selection=[
            ("obligate", "ผูกพัน"),
            ("consume", "ตัดงบ"),
        ],
        string="Type",
        required=True,
        readonly=True,
    )
    amount = fields.Monetary(
        string="จำนวนเงิน",
        required=True,
        currency_field="currency_id",
    )
    name = fields.Char(string="รายละเอียด")
    date = fields.Date(
        string="วันที่",
        default=fields.Date.context_today,
        required=True,
    )

    # Display fields from header (readonly)
    account_id = fields.Many2one(
        related="commitment_id.account_id",
        string="รหัสงบประมาณ",
    )
    department_analytic_id = fields.Many2one(
        related="commitment_id.department_analytic_id",
        string="ส่วนงาน",
    )
    source_analytic_id = fields.Many2one(
        related="commitment_id.source_analytic_id",
        string="แหล่งเงิน",
    )
    activity_analytic_id = fields.Many2one(
        related="commitment_id.activity_analytic_id",
        string="กิจกรรม",
    )
    fund_analytic_id = fields.Many2one(
        related="commitment_id.fund_analytic_id",
        string="กองทุน",
    )
    currency_id = fields.Many2one(
        related="commitment_id.currency_id",
    )

    # Available amount display
    available_amount = fields.Monetary(
        string="คงเหลือ",
        compute="_compute_available_amount",
        currency_field="currency_id",
    )

    @api.depends("commitment_id", "move_type")
    def _compute_available_amount(self):
        for wizard in self:
            if wizard.move_type == "obligate":
                wizard.available_amount = wizard.commitment_id.available_to_obligate
            elif wizard.move_type == "consume":
                wizard.available_amount = wizard.commitment_id.available_to_consume
            else:
                wizard.available_amount = 0

    def action_confirm(self):
        """Create the commitment line with header defaults."""
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Amount must be positive."))

        commitment = self.commitment_id
        vals = {
            "commitment_id": commitment.id,
            "move_type": self.move_type,
            "account_id": commitment.account_id.id,
            "analytic_distribution": commitment.analytic_distribution,
            "amount": self.amount,
            "name": self.name,
            "date": self.date,
        }

        # Pass source document reference from context if provided
        ctx = self.env.context
        if ctx.get("default_res_model"):
            vals["res_model"] = ctx["default_res_model"]
        if ctx.get("default_res_id"):
            vals["res_id"] = ctx["default_res_id"]

        self.env["budget.commitment.line"].create(vals)

        return {"type": "ir.actions.act_window_close"}
