from odoo import _, api, fields, models
from odoo.tools import float_is_zero

_COORDINATE = (
    "account_fiscal_year_id",
    "account_id",
    "department_analytic_id",
    "source_analytic_id",
    "fund_analytic_id",
    "activity_analytic_id",
    "kmitl_project_analytic_id",
    "procurement_plan_analytic_id",
)
_ACTIVE_COMMITMENT_STATES = ("reserved", "partial", "done")


class BudgetLedgerReconcile(models.TransientModel):
    """What the budget ledger and the old two-model formula disagree on.

    Two kinds of row (ADR-0016, Q11): a reservation whose ledger figures differ
    from its posted events, and a (budget code × dimensions) coordinate whose
    ledger Remaining (Σ balance) differs from the old Current − Σ reserve.
    An empty report means the ledger reconciles.
    """

    _name = "budget.ledger.reconcile"
    _description = "Budget Ledger Reconciliation"
    _order = "kind, difference desc, id"

    kind = fields.Selection(
        [("commitment", "ใบจองงบประมาณ"), ("coordinate", "รหัสงบ × มิติ")],
        string="ประเภท",
        required=True,
    )
    metric = fields.Char(string="ตัวเลข")
    commitment_id = fields.Many2one("budget.commitment", string="ใบจองงบประมาณ")
    account_fiscal_year_id = fields.Many2one("account.fiscal.year", string="ปีงบประมาณ")
    account_id = fields.Many2one("budget.account", string="รหัสงบประมาณ")
    department_analytic_id = fields.Many2one(
        "account.analytic.account", string="ส่วนงาน"
    )
    source_analytic_id = fields.Many2one("account.analytic.account", string="แหล่งเงิน")
    fund_analytic_id = fields.Many2one("account.analytic.account", string="กองทุน")
    activity_analytic_id = fields.Many2one("account.analytic.account", string="กิจกรรม")
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account", string="โครงการ/กิจกรรม"
    )
    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account", string="แผนจัดซื้อจัดจ้าง"
    )
    ledger_amount = fields.Float(string="ตามบัญชีงบประมาณ", digits="Budget Precision")
    legacy_amount = fields.Float(string="ตามสูตรเดิม", digits="Budget Precision")
    difference = fields.Float(string="ผลต่าง", digits="Budget Precision")

    @api.model
    def action_open_reconciliation(self):
        """Rebuild the report and open it."""
        self.search([("create_uid", "=", self.env.uid)]).unlink()
        vals_list = self._commitment_rows() + self._coordinate_rows()
        self.create(vals_list)
        return {
            "type": "ir.actions.act_window",
            "name": _("กระทบยอดบัญชีงบประมาณ"),
            "res_model": self._name,
            "view_mode": "tree",
            "domain": [("create_uid", "=", self.env.uid)],
            "context": {"search_default_group_kind": 1},
        }

    def _commitment_rows(self):
        Commitment = self.env["budget.commitment"].sudo()
        commitments = Commitment.search([("state", "!=", "draft")])
        rows = []
        labels = (_("ยอดจองงบ"), _("ยอดผูกพัน"), _("ยอดตัดงบ"))
        for commitment in commitments._ledger_mismatches():
            legacy = commitment._ledger_legacy_totals()
            ledger = (
                commitment.total_reserved,
                commitment.total_obligated,
                commitment.total_consumed,
            )
            for label, old, new in zip(labels, legacy, ledger):
                if float_is_zero(old - new, precision_digits=2):
                    continue
                rows.append(
                    {
                        "kind": "commitment",
                        "metric": label,
                        "commitment_id": commitment.id,
                        "account_fiscal_year_id": commitment.account_fiscal_year_id.id,
                        "account_id": commitment.account_id.id,
                        "ledger_amount": new,
                        "legacy_amount": old,
                        "difference": new - old,
                    }
                )
        return rows

    def _coordinate_rows(self):
        def sums(model, domain, field):
            out = {}
            for grp in (
                self.env[model]
                .sudo()
                .read_group(domain, [field], list(_COORDINATE), lazy=False)
            ):
                key = tuple((grp.get(f) or [False])[0] for f in _COORDINATE)
                out[key] = out.get(key, 0.0) + (grp.get(field) or 0.0)
            return out

        posted = [("parent_state", "=", "posted")]
        ledger = sums("budget.move.line", posted, "balance")
        current = sums(
            "budget.move.line",
            posted + [("move_type", "in", ("appropriation", "entry"))],
            "balance",
        )
        reserved = sums(
            "budget.commitment.line",
            [
                ("state", "=", "posted"),
                ("commitment_id.state", "in", _ACTIVE_COMMITMENT_STATES),
                ("move_type", "=", "reserve"),
            ],
            "amount",
        )
        rows = []
        for key in set(ledger) | set(current) | set(reserved):
            new = ledger.get(key, 0.0)
            old = current.get(key, 0.0) - reserved.get(key, 0.0)
            if float_is_zero(new - old, precision_digits=2):
                continue
            rows.append(
                dict(
                    zip(_COORDINATE, key),
                    kind="coordinate",
                    metric=_("คงเหลือ (f)"),
                    ledger_amount=new,
                    legacy_amount=old,
                    difference=new - old,
                )
            )
        return rows
