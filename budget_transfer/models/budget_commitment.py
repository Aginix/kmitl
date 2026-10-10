from odoo import _, api, models


class BudgetCommitment(models.Model):
    """A reservation moves with the transfers onto/off its coordinate
    (budget ADR-0016, Q5/Q6)."""

    _inherit = "budget.commitment"

    @api.constrains("amount", "state")
    def _check_positive_amount(self):
        """A transfer may release a reservation's whole unobligated remainder:
        its cap then rests at 0 — an empty reservation a later transfer can top
        up again — so a zero cap is allowed while that release posts, or once
        nothing is reserved on it."""
        posting = self.env.context.get("budget_ledger_posting")
        empty = self.filtered(
            lambda c: (
                c.state != "draft"
                and not c.amount
                and (
                    posting
                    or (c.currency_id or self.env.company.currency_id).is_zero(
                        c.total_reserved
                    )
                )
            )
        )
        return super(BudgetCommitment, self - empty)._check_positive_amount()

    def _post_transfer_event(self, transfer_line, amount):
        """Post a ``reserve`` event of ``amount`` (positive = top-up, negative =
        release) as a line inside the transfer's own move, and move the cap.

        The ledger line comes first, so the event is created already posted and
        posts no move of its own; the transfer's move is posted right after.
        """
        self.ensure_one()
        transfer_move = transfer_line.move_id
        source = transfer_move.transfer_ids[:1] or transfer_move
        coordinate = transfer_line._transfer_distribution()
        ledger_line = (
            self.env["budget.move.line"]
            .sudo()
            .with_context(budget_ledger_posting=True)
            .create(
                {
                    "move_id": transfer_move.id,
                    "account_id": transfer_line.account_id.id,
                    "balance": -amount,
                    "analytic_distribution": coordinate,
                    "move_type": "reserve",
                    "commitment_id": self.id,
                }
            )
        )
        event = (
            self.env["budget.commitment.line"]
            .sudo()
            .create(
                {
                    "commitment_id": self.id,
                    "move_type": "reserve",
                    "account_id": transfer_line.account_id.id,
                    "analytic_distribution": coordinate,
                    "amount": amount,
                    "date": transfer_move.date,
                    "res_model": source._name,
                    "res_id": source.id,
                    "budget_move_line_id": ledger_line.id,
                    "name": (
                        _("เพิ่มจองจากการโอนงบ %s")
                        if amount > 0
                        else _("ปลดจองจากการโอนงบ %s")
                    )
                    % transfer_move.display_name,
                }
            )
        )
        ledger_line.with_context(budget_ledger_posting=True).commitment_line_id = event
        self.sudo().with_context(budget_ledger_posting=True).amount += amount
        return event
