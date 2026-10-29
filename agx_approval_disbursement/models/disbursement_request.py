from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # อ้างอิงใบขออนุมัติ: exactly one approved request, whose reservation, budget
    # code and dimensions this ใบขอเบิก inherits (agx_approval ADR-0010).
    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="อ้างอิงใบขออนุมัติ",
        domain=[("state", "=", "approved")],
        ondelete="set null",
        index=True,
        copy=False,
        tracking=True,
    )

    # ค่าใช้จ่ายที่ขอเบิก: which of the request's Expenses this ใบขอเบิก covers,
    # kept apart from the payee lines — the recipient is not always the one who
    # spent (an advance or a loan). Must add up to the ใบขอเบิก's total.
    approval_expense_ids = fields.One2many(
        "disbursement.request.approval.expense",
        "request_id",
        string="ค่าใช้จ่ายที่ขอเบิก",
        # Not copied: approval_request_id is not either, and rows of a ใบขอเบิก
        # that no longer references the request would count against it.
        copy=False,
    )
    approval_expense_unexplained = fields.Monetary(
        string="ยังไม่ได้ชี้แจง",
        currency_field="currency_id",
        compute="_compute_approval_expense_unexplained",
    )

    @api.depends("amount_total", "approval_expense_ids.amount")
    def _compute_approval_expense_unexplained(self):
        for rec in self:
            rec.approval_expense_unexplained = rec.amount_total - sum(
                rec.approval_expense_ids.mapped("amount")
            )

    def _get_source_document(self):
        return self.approval_request_id or super()._get_source_document()

    @api.onchange("approval_request_id")
    def _onchange_approval_request_id(self):
        """Naming the request on the ใบขอเบิก side prefills the same header as
        the request's สร้างใบขอเบิก button."""
        request = self.approval_request_id
        if not request:
            return
        vals = request._disbursement_request_defaults()
        vals.pop("approval_request_id")
        self.update(vals)
        stale = self.approval_expense_ids.filtered(
            lambda r: r.approval_request_line_id.request_id != request._origin
        )
        if stale:
            self.approval_expense_ids -= stale

    def _onchange_fiscal_year_clear_commitment(self):
        # Odoo runs every onchange on a new record's first onchange, which would
        # wipe the commitment prefilled from the approval request; keep one that
        # already belongs to the year.
        commitment = self.budget_commitment_id
        super()._onchange_fiscal_year_clear_commitment()
        if commitment.account_fiscal_year_id == self.account_fiscal_year_id:
            self.budget_commitment_id = commitment

    @api.model_create_multi
    def create(self, vals_list):
        # A ใบขอเบิก naming a request inherits its header unless given one.
        default_request = self.env.context.get("default_approval_request_id")
        for vals in vals_list:
            request_id = vals.get("approval_request_id", default_request)
            if request_id:
                request = self.env["approval.request"].sudo().browse(request_id)
                for key, value in request._disbursement_request_defaults().items():
                    vals.setdefault(key, value)
        records = super().create(vals_list)
        # Checked after create so a request given through default_* context
        # (the สร้างใบขอเบิก action) is caught too, not only one in vals.
        records._check_approval_request_open()
        records._fill_single_approval_expense()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "approval_request_id" in vals:
            self._check_approval_request_open()
        if {"approval_request_id", "line_ids"} & set(vals):
            self._fill_single_approval_expense()
        if {"state", "budget_consumed_amount", "approval_request_id"} & set(vals):
            self.sudo().approval_request_id._disbursement_sync_close()
        return res

    def _check_approval_request_open(self):
        if any(r.state != "approved" for r in self.sudo().approval_request_id):
            raise UserError(
                _("ใบขอเบิกอ้างอิงได้เฉพาะคำขออนุมัติที่ได้รับอนุมัติแล้วและยังไม่ปิด")
            )

    def _check_approval_billing_cap(self):
        """The request's Approved Amount is a hard cap: its disbursed and
        in-progress ใบขอเบิก together may not exceed it (ADR-0010)."""
        for rec in self.filtered("approval_request_id"):
            request = rec.approval_request_id.sudo()
            used = request.disbursed_amount + request.in_progress_amount
            if request.currency_id.compare_amounts(used, request.total_amount) > 0:
                money = request._money
                raise UserError(
                    _(
                        "ยอดใบขอเบิกของ %(request)s รวม %(used)s เกินยอดอนุมัติ "
                        "%(approved)s (เกิน %(over)s)"
                    )
                    % {
                        "request": request.name,
                        "used": money(used),
                        "approved": money(request.total_amount),
                        "over": money(used - request.total_amount),
                    }
                )

    def _fill_single_approval_expense(self):
        """A request with one Expense: the breakdown is that Expense, for the
        whole ใบขอเบิก — kept in step with its total, explanation preserved."""
        for rec in self.filtered("approval_request_id"):
            expenses = rec.approval_request_id.sudo().line_ids
            if len(expenses) != 1 or len(rec.approval_expense_ids) > 1:
                continue
            row = rec.approval_expense_ids
            vals = {"approval_request_line_id": expenses.id, "amount": rec.amount_total}
            if rec.currency_id.compare_amounts(rec.amount_total, 0) <= 0:
                # No total (every line removed): no row, not a 0 that the
                # row's positive-amount constraint rejects.
                row.unlink()
            elif row:
                row.write(vals)
            else:
                rec.approval_expense_ids = [(0, 0, vals)]

    def _check_approval_expenses(self):
        """A ใบขอเบิก that references a request states which of its Expenses it
        covers, adding up to its total."""
        self._fill_single_approval_expense()
        for rec in self.filtered("approval_request_id"):
            request = rec.approval_request_id.sudo()
            if not rec.approval_expense_ids:
                raise UserError(
                    _("กรุณาระบุค่าใช้จ่ายที่ขอเบิก (ตามใบขออนุมัติ %s)") % request.name
                )
            foreign = rec.approval_expense_ids.approval_request_line_id - request.line_ids
            if foreign:
                raise UserError(
                    _("ค่าใช้จ่าย %s ไม่ใช่ของคำขอ %s")
                    % (", ".join(foreign.mapped("name")), request.name)
                )
            if rec.currency_id.compare_amounts(rec.approval_expense_unexplained, 0):
                raise UserError(
                    _(
                        "ค่าใช้จ่ายที่ขอเบิกรวม %(explained)s ไม่เท่ากับยอดใบขอเบิก "
                        "%(total)s (ต่างกัน %(diff)s)"
                    )
                    % {
                        "explained": request._money(
                            rec.amount_total - rec.approval_expense_unexplained
                        ),
                        "total": request._money(rec.amount_total),
                        "diff": request._money(rec.approval_expense_unexplained),
                    }
                )

    @api.constrains("line_ids")
    def _check_approval_billing_cap_on_edit(self):
        # A work-center station may open the lines of a ใบขอเบิก in progress;
        # re-check the cap on any line edit past draft.
        self.filtered(
            lambda r: r.state not in ("draft", "cancel")
        )._check_approval_billing_cap()

    def action_submit(self):
        self._check_approval_request_open()
        self._check_approval_expenses()
        self._check_approval_billing_cap()
        return super().action_submit()

    def action_resubmit_verification(self):
        # A returned ใบขอเบิก skips action_submit on its way back to verification.
        self._check_approval_expenses()
        self._check_approval_billing_cap()
        return super().action_resubmit_verification()

    def action_view_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(_("No Approval Request linked to this request."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Approval Request"),
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
