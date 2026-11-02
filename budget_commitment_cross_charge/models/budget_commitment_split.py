from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetCommitmentSplit(models.Model):
    """Reservation Split (รายการจองงบประมาณ, ADR-0020): one declared code of a
    reservation and the amount it reserves.

    The split is the plan, the reserve events are the command: จองงบ derives one
    reserve event per row, and re-cutting a reserved split cancels them and
    posts new ones. Row ★ is the Primary Code (the header ``account_id``); its
    amount is never typed — it is the วงเงิน minus every ถัว row.
    """

    _name = "budget.commitment.split"
    _description = "Reservation Split"
    _order = "is_primary desc, sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    is_primary = fields.Boolean(
        string="รหัสหลัก",
        readonly=True,
        help="รหัสงบประมาณของใบจอง ยอดของแถวนี้คือวงเงินหักยอดถัวจ่ายของแถวอื่นทั้งหมด",
    )
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        ondelete="restrict",
    )
    amount = fields.Monetary(string="จอง", currency_field="currency_id")
    currency_id = fields.Many2one(related="commitment_id.currency_id")

    available = fields.Monetary(
        string="งบที่จองได้",
        compute="_compute_available",
        currency_field="currency_id",
        help="งบที่จองได้ของรหัสนี้ ณ มิติของใบจอง — รวมยอดที่ใบจองนี้จองรหัสนี้ไว้แล้ว",
    )
    is_sufficient = fields.Boolean(string="พอ", compute="_compute_available")

    # Once reserved: this code's share of the reservation (ADR-0018).
    total_reserved = fields.Monetary(
        string="จองเงิน", compute="_compute_ledger", currency_field="currency_id"
    )
    available_to_consume = fields.Monetary(
        string="ผูกพัน", compute="_compute_ledger", currency_field="currency_id"
    )
    total_consumed = fields.Monetary(
        string="เบิกจ่าย", compute="_compute_ledger", currency_field="currency_id"
    )
    available_to_obligate = fields.Monetary(
        string="คงเหลือ", compute="_compute_ledger", currency_field="currency_id"
    )

    _sql_constraints = [
        (
            "commitment_account_uniq",
            "unique(commitment_id, account_id)",
            "รหัสงบประมาณซ้ำในรายการจองงบประมาณ",
        )
    ]

    @api.depends(
        "account_id",
        "amount",
        "commitment_id.analytic_distribution",
        "commitment_id.account_fiscal_year_id",
        "commitment_id.state",
    )
    def _compute_available(self):
        # sudo: the engine reads every unit's ledger, which a พ.1 committer
        # cannot (root ADR-0010).
        controller = self.env["budget.controller"].sudo()
        for split in self:
            commitment = split.commitment_id
            if not (split.account_id and commitment.account_fiscal_year_id):
                split.available = 0.0
                split.is_sufficient = False
                continue
            available = controller.get_available_detail(
                split.account_id,
                commitment._availability_distribution(),
                commitment.account_fiscal_year_id.id,
                commitment.company_id.id,
            )["available"]
            if commitment._origin and commitment.state != "draft":
                # A re-cut gives this slip's own reservation back first.
                available += commitment._origin._ledger_unobligated(split.account_id)
            split.available = available
            split.is_sufficient = (
                split.currency_id.compare_amounts(split.amount, available) <= 0
                if split.currency_id
                else split.amount <= available
            )

    def _compute_ledger(self):
        sums = {}
        commitments = self.commitment_id._origin
        if commitments:
            groups = (
                self.env["budget.move.line"]
                .sudo()
                .read_group(
                    [
                        ("commitment_id", "in", commitments.ids),
                        ("parent_state", "=", "posted"),
                        ("move_type", "in", ["reserve", "obligate", "consume"]),
                    ],
                    ["balance:sum"],
                    ["commitment_id", "account_id", "move_type"],
                    lazy=False,
                )
            )
            for group in groups:
                key = (group["commitment_id"][0], group["account_id"][0])
                sums.setdefault(key, {})[group["move_type"]] = -(
                    group["balance"] or 0.0
                )
        for split in self:
            buckets = sums.get(
                (split.commitment_id._origin.id, split.account_id.id), {}
            )
            reserve = buckets.get("reserve", 0.0)
            obligate = buckets.get("obligate", 0.0)
            consume = buckets.get("consume", 0.0)
            split.available_to_obligate = reserve
            split.available_to_consume = obligate
            split.total_consumed = consume
            split.total_reserved = reserve + obligate + consume

    # --- Edit windows ---

    def _check_editable(self):
        if self.env.su or self.env.context.get("budget_split_sync"):
            return
        for commitment in self.commitment_id:
            if not commitment.split_editable:
                raise UserError(
                    _("ใบจอง %s แก้ไขรายการจองงบประมาณ (ถัวจ่าย) ในขั้นนี้ไม่ได้")
                    % commitment.display_name
                )

    @api.model_create_multi
    def create(self, vals_list):
        splits = super().create(vals_list)
        splits._check_editable()
        splits._notify_changed()
        return splits

    def write(self, vals):
        self._check_editable()
        res = super().write(vals)
        if {"account_id", "amount"} & set(vals):
            self._notify_changed()
        return res

    def unlink(self):
        self._check_editable()
        commitments = self.commitment_id
        res = super().unlink()
        self._notify_changed(commitments.exists())
        return res

    def _notify_changed(self, commitments=None):
        """Re-derive the primary row (and re-cut a reserved slip) — once per
        form save: the commitment's own write does it after all its rows, and
        the sync's own writes never re-enter."""
        context = self.env.context
        if context.get("budget_split_sync") or context.get("budget_split_batch"):
            return
        (
            commitments if commitments is not None else self.commitment_id
        )._on_split_changed()
