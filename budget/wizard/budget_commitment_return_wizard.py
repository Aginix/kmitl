import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# The coordinate rows the widget shows, in this order; empty rows are skipped
# (same order as the commitment form and the โอนคืนงบลอย wizard).
_DIM_ROWS = (
    ("source_analytic_id", "แหล่งเงิน"),
    ("department_analytic_id", "ส่วนงาน"),
    ("fund_analytic_id", "กองทุน"),
    ("activity_analytic_id", "ด้าน/แผนงาน/กิจกรรม"),
    ("account_id", "รหัสงบประมาณ"),
    ("kmitl_project_analytic_id", "โครงการ/กิจกรรม"),
    ("procurement_plan_analytic_id", "แผนจัดซื้อจัดจ้าง"),
)
# display_name is "[code] parent / … / leaf" — strip the code prefix.
_CODE_PREFIX = re.compile(r"^\[[^\]]*\]\s*")


class BudgetCommitmentReturnWizard(models.TransientModel):
    """Confirmation wizard to return leftover reserved budget (ส่งคืนเงินเหลือจ่าย).

    Read-only confirmation: it shows the computed return amount (the unobligated
    remainder of the reservation, จอง − ผูกพัน), the budget code and analytic
    dimensions, then
    posts a single negative ``reserve`` line (``is_return=True``) to release the
    earmark back to the pool. The commitment is not cancelled; it auto-closes to
    ``done`` once the leftover is returned. See ``budget/CONTEXT.md``
    (Return Unused Reservation / คืนจอง) and ADR-0009.
    """

    _name = "budget.commitment.return.wizard"
    _description = "Return Leftover Reserved Budget"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        readonly=True,
    )
    # Shown for context alongside ส่งคืน (= จองทั้งหมด − ผูกพัน = available_to_obligate):
    # จองทั้งหมด and เบิกจ่ายแล้ว — these reconcile as จอง − เบิก = ส่งคืน only under the
    # current obligate≡consume flow (ADR-0001); once obligate runs ahead they will not.
    total_reserved = fields.Monetary(
        related="commitment_id.total_reserved",
        string="ยอดจองทั้งหมด",
        currency_field="currency_id",
    )
    total_consumed = fields.Monetary(
        related="commitment_id.total_consumed",
        string="เบิกจ่ายแล้ว",
        currency_field="currency_id",
    )
    return_amount = fields.Monetary(
        related="commitment_id.available_to_obligate",
        string="ยอดส่งคืน",
        currency_field="currency_id",
        help="ยอดเงินจองที่ยังไม่ได้ผูกพัน ซึ่งจะถูกส่งคืนเข้ากระเป๋างบประมาณ",
    )
    name = fields.Char(
        string="รายละเอียด",
        default=lambda self: _("ส่งคืนเงินเหลือจ่าย"),
    )
    date = fields.Date(
        string="วันที่",
        default=fields.Date.context_today,
        required=True,
    )

    currency_id = fields.Many2one(related="commitment_id.currency_id")

    # --- read by the budget_commitment_return widget ----------------------
    step = fields.Selection(
        [("review", "ตรวจสอบ"), ("done", "สำเร็จ")],
        default="review",
        required=True,
    )
    commitment_label = fields.Char(compute="_compute_widget_info")
    commitment_dims = fields.Char(compute="_compute_widget_info")
    available_to_consume = fields.Monetary(
        related="commitment_id.available_to_consume",
        currency_field="currency_id",
    )
    # The slip: the posted return line, and the amount it returned (the live
    # return_amount drops to 0 once posted).
    return_line_id = fields.Many2one("budget.commitment.line", readonly=True)
    returned_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    return_ref = fields.Char(related="return_line_id.budget_move_id.name")
    return_date = fields.Datetime(related="return_line_id.create_date")
    return_user_id = fields.Many2one(related="return_line_id.create_uid")

    @api.depends("commitment_id")
    def _compute_widget_info(self):
        for wiz in self:
            commitment = wiz.commitment_id
            wiz.commitment_label = " - ".join(
                filter(None, [commitment.name, commitment.title])
            )
            rows = []
            for key, label in _DIM_ROWS:
                record = commitment[key] if key in commitment._fields else False
                if not record:
                    continue
                names = _CODE_PREFIX.sub("", record.display_name or "").split(" / ")
                rows.append(
                    {
                        "key": key,
                        "label": label,
                        "code": record.code or "",
                        "path": names[:-1],
                        "leaf": names[-1],
                    }
                )
            wiz.commitment_dims = json.dumps(rows, ensure_ascii=False)

    def action_confirm(self):
        """Post the negative reserve line (คืนจอง) for the leftover remainder.

        The amount is re-read from the commitment at confirm time (not the cached
        display value) so a concurrent consume cannot let us over-return. The
        account and dimensions are taken from the first posted reserve line — the
        same convention the disbursement consume flow uses — so the reversal nets
        at the original control node. A single aggregate line is the only
        well-defined return because consume never splits per budget code (ADR-0009).
        """
        self.ensure_one()
        # Carry the source document through from the opener (e.g. a DR), mirroring
        # the consume flow's res_model/res_id stamping for drill-down traceability.
        ctx = self.env.context
        source = None
        if ctx.get("default_res_model") and ctx.get("default_res_id"):
            source = self.env[ctx["default_res_model"]].browse(ctx["default_res_id"])
        line = self.commitment_id._return_leftover(
            source=source, name=self.name, date=self.date
        )
        if not line:
            raise UserError(_("No leftover reserved budget to return."))
        self.write(
            {"step": "done", "return_line_id": line.id, "returned_amount": -line.amount}
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("ส่งคืนเงินเหลือจ่าย"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
