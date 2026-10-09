from odoo import _, api, fields, models
from odoo.exceptions import UserError

# A posted ledger line of a commitment event is the figure itself: its amount,
# budget code and coordinate may not change afterwards — undo the event instead.
_LEDGER_LOCKED_FIELDS = frozenset(
    {
        "balance",
        "debit",
        "credit",
        "account_id",
        "analytic_distribution",
        "activity_analytic_id",
        "department_analytic_id",
        "fund_analytic_id",
        "kmitl_project_analytic_id",
        "procurement_plan_analytic_id",
        "move_type",
        "commitment_id",
        "move_id",
    }
)


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    # The bucket a line moves (ADR-0016, Q4): defaults to the move's type, but
    # a liquidation line inside an obligate/consume move — or a reservation
    # top-up inside a transfer move — names its own bucket.
    move_type = fields.Selection(
        selection="_selection_move_type",
        related=False,
        compute="_compute_move_type",
        store=True,
        readonly=False,
        index=True,
    )
    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="ใบจองงบประมาณ",
        index=True,
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    commitment_line_id = fields.Many2one(
        comodel_name="budget.commitment.line",
        string="เหตุการณ์ใบจอง",
        index=True,
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    is_liquidation = fields.Boolean(
        string="ปลดจอง",
        readonly=True,
        copy=False,
        help="Moves money out of the previous bucket as a reservation advances "
        "(reserve → obligate → consume).",
    )
    is_return = fields.Boolean(
        string="ส่งคืนเงินเหลือจ่าย",
        readonly=True,
        copy=False,
    )

    @api.model
    def _selection_move_type(self):
        return (
            self.env["budget.move"]
            ._fields["move_type"]
            ._description_selection(self.env)
        )

    @api.depends("move_id.move_type")
    def _compute_move_type(self):
        for line in self:
            line.move_type = line.move_id.move_type

    def write(self, vals):
        if _LEDGER_LOCKED_FIELDS & set(vals) and not self.env.context.get(
            "budget_ledger_posting"
        ):
            if self.filtered(
                lambda line: line.commitment_id and line.parent_state == "posted"
            ):
                raise UserError(
                    _(
                        "Cannot edit a posted budget ledger line of a commitment. "
                        "Cancel the commitment event instead."
                    )
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Pool-tag owner (ADR-0016, Q5)
    # ------------------------------------------------------------------
    def _get_pool_owner_commitment(self):
        """Reservations owned by this line's pool tag.

        Empty here; ``kmitl_project_budget_ledger`` / ``procurement_plan_budget_ledger``
        return the reservations of the project / plan the tag names.
        """
        self.ensure_one()
        return self.env["budget.commitment"]

    def _ledger_pool_owner(self):
        """The active reservation sitting on exactly this line's coordinate
        (budget code, every dimension, fiscal year) and owning its pool tag."""
        self.ensure_one()
        if not self.account_id or not self.move_id.account_fiscal_year_id:
            return self.env["budget.commitment"]
        coordinate = {int(key) for key in self._ledger_coordinate()}
        return (
            self._get_pool_owner_commitment()
            .filtered(
                lambda c: (
                    c.state in ("reserved", "partial", "done")
                    and c.account_id == self.account_id
                    and c.account_fiscal_year_id == self.move_id.account_fiscal_year_id
                    and {int(key) for key in (c.analytic_distribution or {})}
                    == coordinate
                )
            )
            .sorted("id")[:1]
        )

    def _ledger_coordinate(self):
        """{analytic_id: 100} over every present dimension, from the columns."""
        self.ensure_one()
        if "transfer_direction" in self._fields and self.transfer_direction:
            return self._transfer_distribution()
        return dict(self.analytic_distribution or {})

    def _ledger_free_budget(self):
        """Unreserved money at this transfer line's coordinate (the engine's
        Available — reservations are already netted into the ledger)."""
        self.ensure_one()
        move = self.move_id
        return self.env["budget.controller"].get_available(
            self.account_id,
            self._ledger_coordinate(),
            move.account_fiscal_year_id.id,
            self.company_id.id or move.company_id.id,
        )

    def _compute_transfer_availability(self):
        """A FROM line out of a reserved coordinate may also draw what the
        owning reservation still has unobligated: posting draws the free money
        first and releases only the rest (ADR-0016, Q5)."""
        res = super()._compute_transfer_availability()
        for line in self:
            move = line.move_id
            if not (
                line.transfer_direction == "from"
                and line.account_id
                and move.move_type != "appropriation"
                and move.account_fiscal_year_id
            ):
                continue
            owner = line._ledger_pool_owner()
            if owner:
                line.available_budget += max(
                    owner._ledger_unobligated(line.account_id), 0.0
                )
                line.budget_sufficient = line.available_budget >= (line.amount or 0.0)
        return res
