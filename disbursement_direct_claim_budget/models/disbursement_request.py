# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    """Budget control of a ตั้งเบิกตรง (disbursement ADR-0005).

    A direct claim may still draw a reservation and is then consumed through
    it like any request. Without one it carries its own dimensions and budget
    code, and its final approval posts a direct consumption (ตัดงบตรง, budget
    ADR-0019) that cancelling the request undoes.
    """

    _inherit = "disbursement.request"

    budget_direct_move_id = fields.Many2one(
        "budget.move",
        string="Direct Consumption",
        copy=False,
        readonly=True,
        ondelete="restrict",
    )

    def _action_approve_budget(self):
        self.ensure_one()
        if self.is_direct_claim and not self.budget_commitment_id:
            return self._consume_direct()
        return super()._action_approve_budget()

    def _consume_direct(self):
        """Post a direct consumption for the request's amount on its own
        dimensions and budget code.

        The request's approval chain stands in for the Budget-Manager right
        (``budget_direct_consume_by_document``); the pool and dimension checks
        still run on posting, so an exhausted pool aborts the approval.
        """
        self.ensure_one()
        # Idempotent across a return-to-verification round trip. Read as sudo:
        # the approver need not hold any budget right.
        if self.sudo().budget_direct_move_id.state == "posted":
            return
        if not self.budget_account_id:
            raise UserError(_("A direct claim needs a budget code before approval."))
        dims = self.env["budget.controller"]._parse_dimensions(
            self.analytic_distribution
        )
        no_dim = self.env["account.analytic.account"]
        line_dims = {
            column: account.id
            for column, account in dims.items()
            # Related to the move's header on the line.
            if column != "source_analytic_id"
        }
        Move = self.env["budget.move"].sudo()
        vals = {
            "move_type": "consume",
            "budget_type": "expense",
            "ref": self.name,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "company_id": self.company_id.id,
            "department_analytic_id": dims.get("department_analytic_id", no_dim).id,
            "source_analytic_id": dims.get("source_analytic_id", no_dim).id,
            "line_ids": [
                (
                    0,
                    0,
                    dict(
                        line_dims,
                        account_id=self.budget_account_id.id,
                        balance=-self.amount_total,
                    ),
                )
            ],
        }
        # budget_operating_unit would stamp the approver's unit; the
        # consumption belongs to the requester's.
        if "operating_unit_id" in Move._fields:
            unit = self.user_id.sudo().default_operating_unit_id
            if unit:
                vals["operating_unit_id"] = unit.id
        move = Move.create(vals)
        move.action_review()
        move.with_context(budget_direct_consume_by_document=True).action_post()
        self.budget_direct_move_id = move
        self.budget_consumed_amount = self.amount_total
        self.budget_consumed_date = fields.Datetime.now()
        self.message_post(
            body=_("Budget consumed directly: %(amount)s (%(move)s)")
            % {"amount": self.amount_total, "move": move.name},
            subtype_xmlid="mail.mt_note",
        )

    def _direct_claim_budget_shortfall(self):
        """Whether the pool cannot cover this direct claim without a
        reservation — the Submit pre-check; the posting re-checks it on the
        final approval. A linked reservation is checked on approval instead."""
        self.ensure_one()
        if (
            self.budget_commitment_id
            or not self.budget_account_id
            or self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        ):
            return False
        available = (
            self.env["budget.controller"]
            .sudo()
            .get_available(
                self.budget_account_id.id,
                self.analytic_distribution,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        )
        return self.currency_id.compare_amounts(available, self.amount_total) < 0

    def _on_cancel(self):
        for rec in self:
            direct = rec.sudo().budget_direct_move_id
            if direct.state == "posted":
                direct.with_context(
                    budget_direct_consume_by_document=True
                ).button_cancel()
                rec.message_post(
                    body=_("Direct consumption %s cancelled.") % direct.name,
                    subtype_xmlid="mail.mt_note",
                )
        # Resets budget_consumed_amount / _date.
        return super()._on_cancel()
