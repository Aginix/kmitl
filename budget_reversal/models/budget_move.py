from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

# Only pool-building moves are reversed; a commitment event is undone by
# cancelling the event (budget ADR-0017).
_REVERSIBLE_TYPES = ("appropriation", "entry")


class BudgetMove(models.Model):
    """Budget Reversal (กลับรายการ, budget ADR-0020).

    A posted appropriation/entry move — a manual budget move or the move of a
    budget transfer — is corrected by a new **draft** move offsetting it, while
    the original stays posted. The draft is an ordinary budget move: freely
    editable (a partial reversal is just a smaller one) and posted through the
    normal review → post workflow, but it may not take back money its pool no
    longer has free.
    """

    _inherit = "budget.move"

    reversed_move_id = fields.Many2one(
        comodel_name="budget.move",
        string="กลับรายการของ",
        readonly=True,
        copy=False,
        index=True,
        ondelete="restrict",
    )
    reversal_move_ids = fields.One2many(
        comodel_name="budget.move",
        inverse_name="reversed_move_id",
        string="รายการกลับรายการ",
        readonly=True,
    )
    reversal_count = fields.Integer(compute="_compute_reversal_status")
    reversal_status = fields.Selection(
        selection=[
            ("partial", "กลับรายการบางส่วน"),
            ("full", "กลับรายการแล้ว"),
        ],
        string="สถานะกลับรายการ",
        compute="_compute_reversal_status",
    )
    can_reverse = fields.Boolean(compute="_compute_can_reverse")

    @api.depends(
        "line_ids.balance",
        "reversal_move_ids.state",
        "reversal_move_ids.line_ids.balance",
    )
    def _compute_reversal_status(self):
        """Fully reversed when, per coordinate, the original and its posted
        reversals net to zero; any other posted reversal is partial."""
        for move in self:
            move.reversal_count = len(move.reversal_move_ids)
            posted = move.reversal_move_ids.filtered(lambda m: m.state == "posted")
            if not posted:
                move.reversal_status = False
                continue
            net = defaultdict(float)
            for line in (move | posted).line_ids.filtered(
                lambda move_line: move_line.move_type in _REVERSIBLE_TYPES
            ):
                net[line._reversal_key()] += line.balance
            rounding = move.currency_id.rounding or 0.01
            fully = all(
                float_is_zero(amount, precision_rounding=rounding)
                for amount in net.values()
            )
            move.reversal_status = "full" if fully else "partial"

    @api.depends("state", "move_type", "reversed_move_id")
    def _compute_can_reverse(self):
        for move in self:
            move.can_reverse = bool(move.id) and move._is_reversible()

    @api.constrains("date", "account_fiscal_year_id", "reversed_move_id")
    def _check_reversal_fiscal_year(self):
        """A reversal offsets the pool of the original's fiscal year."""
        for move in self.filtered("reversed_move_id"):
            fiscal_year = move.reversed_move_id.account_fiscal_year_id
            if move.account_fiscal_year_id != fiscal_year or not (
                fiscal_year.date_from <= move.date <= fiscal_year.date_to
            ):
                raise ValidationError(
                    _(
                        "A reversal must stay in the fiscal year of the move it "
                        "reverses (%s)."
                    )
                    % fiscal_year.display_name
                )

    def _is_reversible(self):
        """Hook: whether กลับรายการ may be done on this move. Bridges exclude
        the moves another document owns."""
        self.ensure_one()
        return (
            self.state == "posted"
            and self.move_type in _REVERSIBLE_TYPES
            and not self.reversed_move_id
        )

    def _prepare_reversal_defaults(self):
        """``copy()`` defaults of the reversal: the header follows the original
        (fiscal year, dimensions, operating unit…); the lines are its pool lines
        negated — a transfer's reservation top-ups stay out (they are undone by
        returning the reservation)."""
        self.ensure_one()
        fiscal_year = self.account_fiscal_year_id
        date = max(
            fiscal_year.date_from,
            min(fields.Date.context_today(self), fiscal_year.date_to),
        )
        lines = self.line_ids.filtered(
            lambda move_line: (
                move_line.move_type in _REVERSIBLE_TYPES and not move_line.commitment_id
            )
        )
        return {
            "date": date,
            "ref": _("กลับรายการ: %s") % self.name,
            "reversed_move_id": self.id,
            "line_ids": [
                Command.create(
                    {
                        "account_id": line.account_id.id,
                        "analytic_distribution": line._ledger_coordinate(),
                        "move_type": line.move_type,
                        "balance": -line.balance,
                        "note": line.note,
                    }
                )
                for line in lines
            ],
        }

    def action_reverse(self):
        """กลับรายการ: create the offsetting draft move and open it."""
        self.ensure_one()
        if not self._is_reversible():
            raise UserError(_("Budget move %s cannot be reversed.") % self.display_name)
        reversal = self.copy(self._prepare_reversal_defaults())
        self.message_post(
            body=_("กลับรายการ: %s") % reversal._get_html_link(),
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("กลับรายการ"),
            "res_model": "budget.move",
            "res_id": reversal.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_reversals(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการกลับรายการ"),
            "res_model": "budget.move",
            "view_mode": "tree,form",
            "domain": [("reversed_move_id", "=", self.id)],
            "context": {"create": False},
        }

    def action_post(self):
        self.filtered("reversed_move_id")._check_reversal_availability()
        return super().action_post()

    def _check_reversal_availability(self):
        """A reversal may not take back money its pool no longer has free
        (ADR-0020): the amount it draws from each control node must fit that
        node's Available — reserved money must be returned (คืนจอง) first.
        Summed per control node, like a direct consumption (ADR-0019)."""
        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        ):
            return
        controller = self.env["budget.controller"]
        for move in self.filtered(lambda m: m.budget_type == "expense"):
            rounding = move.currency_id.rounding or 0.01
            pools = {}
            for line in move.line_ids.filtered(
                lambda move_line: move_line.move_type in _REVERSIBLE_TYPES
            ):
                detail = controller.get_available_detail(
                    line.account_id,
                    line._ledger_coordinate(),
                    move.account_fiscal_year_id.id,
                    move.company_id.id,
                )
                pool = detail["pool"]
                if pool:
                    key = (
                        pool["account"]["id"],
                        *sorted(info["id"] for info in pool["dims"].values()),
                    )
                else:
                    key = ("uncovered", line.id)
                entry = pools.setdefault(
                    key,
                    {
                        "amount": 0.0,
                        "available": detail["available"],
                        "accounts": line.account_id.browse(),
                    },
                )
                entry["amount"] -= line.balance
                entry["accounts"] |= line.account_id
            for entry in pools.values():
                if (
                    float_compare(entry["amount"], 0.0, precision_rounding=rounding)
                    <= 0
                ):
                    continue
                if (
                    float_compare(
                        entry["available"], entry["amount"], precision_rounding=rounding
                    )
                    < 0
                ):
                    raise UserError(
                        _(
                            "Cannot post reversal %(move)s: it takes back "
                            "%(amount).2f from %(code)s but only %(available).2f "
                            "is available at the control node. Return or cancel "
                            "the reservations on it first."
                        )
                        % {
                            "move": move.display_name,
                            "amount": entry["amount"],
                            "code": ", ".join(entry["accounts"].mapped("display_name")),
                            "available": entry["available"],
                        }
                    )

    def button_draft(self):
        """The original of a live reversal stays posted: resetting it would
        undo the same money twice."""
        reversed_moves = self.filtered(
            lambda m: m.reversal_move_ids.filtered(lambda r: r.state != "cancel")
        )
        if reversed_moves:
            raise UserError(
                _(
                    "Cannot reset %s to draft: it has a reversal (กลับรายการ) "
                    "that is not cancelled. Cancel the reversal first."
                )
                % ", ".join(reversed_moves.mapped("display_name"))
            )
        return super().button_draft()
