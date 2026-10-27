# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError


class DisbursementRequest(models.Model):
    """ปันส่วน (disbursement ADR-0009).

    Part of the income a request disburses is apportioned to units inside the
    institute instead of being paid. The consume-budget act consumes the payee
    lines directly from the pool (no reservation) and, in the same
    transaction, posts a budget transfer of the apportioned share from the
    request's budget code and dimensions to each apportionment line.
    """

    _inherit = "disbursement.request"

    is_apportioned = fields.Boolean(
        string="Apportioned",
        tracking=True,
        copy=False,
    )
    apportionment_line_ids = fields.One2many(
        "disbursement.apportionment.line",
        "request_id",
        string="Apportionment Lines",
        copy=False,
    )
    apportionment_amount = fields.Monetary(
        string="Apportioned",
        compute="_compute_apportionment_amount",
        store=True,
        currency_field="currency_id",
    )
    budget_total_amount = fields.Monetary(
        string="Budget Total",
        compute="_compute_apportionment_amount",
        store=True,
        currency_field="currency_id",
        help="The request's total plus its apportionment: what it takes out "
        "of its own budget code and dimensions.",
    )
    apportionment_transfer_id = fields.Many2one(
        "budget.transfer",
        string="Apportionment Transfer",
        copy=False,
        readonly=True,
        ondelete="restrict",
    )

    @api.depends("is_apportioned", "apportionment_line_ids.amount", "amount_total")
    def _compute_apportionment_amount(self):
        for rec in self:
            rec.apportionment_amount = (
                sum(rec.apportionment_line_ids.mapped("amount"))
                if rec.is_apportioned
                else 0.0
            )
            rec.budget_total_amount = rec.amount_total + rec.apportionment_amount

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # After super(): the flag may also come from a default_ context key.
        if records.filtered("is_apportioned"):
            self._check_apportionment_right()
        return records

    def write(self, vals):
        if "is_apportioned" in vals and self.filtered(
            lambda r: r.is_apportioned != bool(vals["is_apportioned"])
        ):
            self._check_apportionment_right()
        return super().write(vals)

    def _check_apportionment_right(self):
        """Only users granted ปันส่วน may tick or untick it."""
        if not self.env.su and not self.env.user.has_group(
            "disbursement_apportionment.group_disbursement_apportionment"
        ):
            raise AccessError(
                _("Only users with the Apportionment right may set or clear it.")
            )

    # -------------------------------------------------------------------------
    # Budget
    # -------------------------------------------------------------------------
    def _action_approve_budget(self):
        self.ensure_one()
        if not self.is_apportioned:
            return super()._action_approve_budget()
        if self.budget_commitment_id:
            raise UserError(
                _("An apportioned request is consumed without a budget commitment.")
            )
        self._consume_direct()
        self._post_apportionment_transfer()

    def _direct_claim_budget_shortfall(self):
        """For an apportioned request the pool must cover the budget total —
        the consumption and the transfer out of the same coordinate."""
        self.ensure_one()
        if not self.is_apportioned:
            return super()._direct_claim_budget_shortfall()
        if self.budget_commitment_id or not self.budget_account_id:
            return False
        vals = self._prepare_direct_consume_vals()
        vals["line_ids"][0][2]["balance"] = -self.budget_total_amount
        move = self.env["budget.move"].sudo().new(vals)
        try:
            move.line_ids._check_direct_consume()
        except UserError:
            return True
        return False

    def _prepare_apportionment_transfer_vals(self):
        self.ensure_one()
        dims = self.env["budget.controller"]._parse_dimensions(
            self.analytic_distribution
        )
        no_dim = self.env["account.analytic.account"]
        lines = [
            Command.create(
                {
                    "transfer_direction": "from",
                    "account_id": self.budget_account_id.id,
                    "amount": self.apportionment_amount,
                    "analytic_distribution": self.analytic_distribution,
                }
            )
        ] + [
            Command.create(
                {
                    "transfer_direction": "to",
                    "account_id": line.budget_account_id.id,
                    "amount": line.amount,
                    "analytic_distribution": line._transfer_distribution(),
                }
            )
            for line in self.apportionment_line_ids
        ]
        vals = {
            "date": fields.Date.context_today(self),
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "department_analytic_id": dims.get("department_analytic_id", no_dim).id,
            "source_analytic_id": dims.get("source_analytic_id", no_dim).id,
            "reason": _("ปันส่วนตามใบขอเบิก %s") % self.name,
            "disbursement_request_id": self.id,
            "line_ids": lines,
        }
        Transfer = self.env["budget.transfer"]
        if "operating_unit_id" in Transfer._fields:
            # The request's unit, not the approver's default.
            unit = (
                "operating_unit_id" in self._fields and self.sudo().operating_unit_id
            ) or self.user_id.sudo().default_operating_unit_id
            if unit:
                vals["operating_unit_id"] = unit.id
        return vals

    def _post_apportionment_transfer(self):
        """Create the apportionment transfer, run the ordinary ยืนยัน checks
        and post it at once (ADR-0009). Idempotent across a divert back. As
        sudo: the consume act's role stands in for the Budget rights."""
        self.ensure_one()
        if self.sudo().apportionment_transfer_id.state == "posted":
            return
        if not self.apportionment_line_ids:
            raise UserError(_("An apportioned request needs apportionment lines."))
        transfer = (
            self.env["budget.transfer"]
            .sudo()
            .create(self._prepare_apportionment_transfer_vals())
        )
        transfer.action_submit()
        if transfer.state != "submitted":
            # The exception framework returned its review popup instead of
            # raising; surface its rules here (rolls the consumption back).
            names = (
                transfer.exception_ids.mapped("name")
                if "exception_ids" in transfer._fields
                else []
            )
            raise UserError(
                "\n".join([_("Cannot post the apportionment transfer:")] + names)
            )
        transfer.write(
            {"approver_id": self.env.uid, "approval_date": fields.Datetime.now()}
        )
        transfer._post_transfer()
        self.apportionment_transfer_id = transfer
        self.message_post(
            body=_("Apportioned %(amount)s by budget transfer %(name)s")
            % {"amount": self.apportionment_amount, "name": transfer.name},
            subtype_xmlid="mail.mt_note",
        )

    def _on_cancel(self):
        # The transfer is not reversed (ADR-0009): say so where it is noticed.
        for rec in self:
            transfer = rec.sudo().apportionment_transfer_id
            if transfer.state == "posted":
                rec.message_post(
                    body=_(
                        "Apportionment transfer %s stays posted; a Budget "
                        "Manager reverses it if needed."
                    )
                    % transfer.name,
                    subtype_xmlid="mail.mt_note",
                )
        return super()._on_cancel()

    def action_view_apportionment_transfer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Apportionment Transfer"),
            "res_model": "budget.transfer",
            "res_id": self.apportionment_transfer_id.id,
            "view_mode": "form",
            "target": "current",
        }
