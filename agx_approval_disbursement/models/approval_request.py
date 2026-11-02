from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang, plaintext2html


class ApprovalRequest(models.Model):
    """Disbursing an approved request over time (agx_approval ADR-0010):
    finance raises any number of ใบขอเบิก against it, each line paying one of
    its Expenses; Approved Amount − Disbursed − In-progress = Remaining; it
    closes by itself at zero or by finance's hand, returning the leftover."""

    _inherit = "approval.request"

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="approval_request_id",
        string="Disbursement Requests",
    )

    disbursement_request_count = fields.Integer(
        string="Disbursement Request Count",
        compute="_compute_disbursement_request",
    )

    # Stored so finance can list, sort and filter the requests open for
    # disbursement; computed as superuser — the requester may not read DRs.
    disbursed_amount = fields.Monetary(
        string="เบิกจ่ายแล้ว",
        currency_field="currency_id",
        compute="_compute_disbursement_figures",
        store=True,
        help="ยอดใบขอเบิกของคำขอนี้ที่ตัดงบแล้ว",
    )
    in_progress_amount = fields.Monetary(
        string="อยู่ระหว่างเบิก",
        currency_field="currency_id",
        compute="_compute_disbursement_figures",
        store=True,
        help="ยอดใบขอเบิกที่ยังไม่ยกเลิกและยังไม่ตัดงบ รวมฉบับร่าง",
    )
    remaining_amount = fields.Monetary(
        string="คงเหลือ",
        currency_field="currency_id",
        compute="_compute_disbursement_figures",
        store=True,
        help="ยอดอนุมัติ − เบิกจ่ายแล้ว − อยู่ระหว่างเบิก − ยอดที่ปิดไปเมื่อปิดคำขอ",
    )
    # What Close gave back: the Remaining at that moment — returned to the
    # budget (leftover_returned_amount) or left in a shared reservation.
    closed_amount = fields.Monetary(
        string="ปิดยอด",
        currency_field="currency_id",
        readonly=True,
        copy=False,
        tracking=True,
    )
    leftover_returned_amount = fields.Monetary(
        string="ส่งคืนเงินเหลือจ่ายแล้ว",
        currency_field="currency_id",
        readonly=True,
        copy=False,
        tracking=True,
    )
    disbursement_overview = fields.Json(
        compute="_compute_disbursement_overview",
    )

    # -- figures -----------------------------------------------------------
    def _active_disbursements(self):
        self.ensure_one()
        return self.sudo().disbursement_request_ids.filtered(
            lambda d: d.state != "cancel"
        )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_request(self):
        for record in self:
            record.disbursement_request_count = len(record.disbursement_request_ids)

    @api.depends(
        "total_amount",
        "closed_amount",
        "disbursement_request_ids.state",
        "disbursement_request_ids.amount_total",
        "disbursement_request_ids.budget_consumed_amount",
    )
    def _compute_disbursement_figures(self):
        for record in self:
            active = record._active_disbursements()
            consumed = active.filtered("budget_consumed_amount")
            record.disbursed_amount = sum(consumed.mapped("budget_consumed_amount"))
            record.in_progress_amount = sum((active - consumed).mapped("amount_total"))
            record.remaining_amount = (
                record.total_amount
                - record.disbursed_amount
                - record.in_progress_amount
                - record.closed_amount
            )

    def _money(self, amount):
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    @api.depends(
        "state",
        "total_amount",
        "line_ids.name",
        "line_ids.description",
        "line_ids.total_amount",
        "disbursed_amount",
        "in_progress_amount",
        "remaining_amount",
        "closed_amount",
        "leftover_returned_amount",
    )
    @api.depends_context("uid")
    def _compute_disbursement_overview(self):
        """Everything the ภาพรวมการเบิกจ่าย widget draws, read as superuser so
        the requester (who may not read ใบขอเบิก) sees it too. DR links are
        offered only to users who may open a ใบขอเบิก. Not compute_sudo: the
        value depends on the user, which a sudo cache key would not carry."""
        DR = self.env["disbursement.request"]
        can_open = DR.check_access_rights("read", raise_exception=False)
        state_labels = dict(DR._fields["state"]._description_selection(self.env))
        for record in self:
            if record.state not in ("approved", "done"):
                record.disbursement_overview = False
                continue
            sudo = record.sudo()
            per_line = sudo.line_ids._disbursement_figures()
            expenses = []
            for line in sudo.line_ids:
                disbursed, in_progress = per_line.get(line.id, (0.0, 0.0))
                remaining = line.total_amount - disbursed - in_progress
                expenses.append(
                    {
                        "name": line.name,
                        "description": line.description or "",
                        "amount": line.total_amount,
                        "disbursed": disbursed,
                        "in_progress": in_progress,
                        "remaining": remaining,
                        "over": record.currency_id.compare_amounts(remaining, 0) < 0,
                    }
                )
            requests = []
            for dr in sudo.disbursement_request_ids.sorted("id"):
                consumed = bool(dr.budget_consumed_amount)
                requests.append(
                    {
                        "id": dr.id,
                        "name": dr.display_name,
                        "memo_number": dr.memo_number or "",
                        "amount": dr.amount_total,
                        "state": state_labels.get(dr.state, dr.state),
                        "stage": "cancel"
                        if dr.state == "cancel"
                        else ("disbursed" if consumed else "in_progress"),
                    }
                )
            record.disbursement_overview = {
                "approved": record.total_amount,
                "disbursed": record.disbursed_amount,
                "in_progress": record.in_progress_amount,
                "remaining": record.remaining_amount,
                "closed": record.closed_amount,
                "returned": record.leftover_returned_amount,
                "shared": bool(sudo.reservation_commitment_id),
                "state": record.state,
                "expenses": expenses,
                "requests": requests,
                "can_open": can_open,
            }

    # -- ใบขอเบิก ------------------------------------------------------------
    def _disbursement_note(self):
        """The DR's Html note from ``description`` — Text here, Html when
        agx_approval_description_html is installed."""
        self.ensure_one()
        if not self.description or self._fields["description"].type == "html":
            return self.description
        return plaintext2html(self.description)

    def _disbursement_request_defaults(self):
        """The header a ใบขอเบิก inherits from this request."""
        self.ensure_one()
        vals = {
            "approval_request_id": self.id,
            "note": self._disbursement_note(),
            "budget_commitment_id": self.budget_commitment_id.id,
            "budget_account_id": self.budget_account_id.id,
            "analytic_distribution": self.analytic_distribution,
        }
        if self.budget_commitment_id:
            # Book to the commitment's year (an FY69 reservation disbursed in
            # FY70), as disbursement_budget's create does.
            vals["account_fiscal_year_id"] = (
                self.budget_commitment_id.account_fiscal_year_id.id
            )
        return vals

    def action_create_disbursement_request(self):
        """Open a new ใบขอเบิก against this request, its header prefilled —
        finance enters the payee type, recipients, lines and banks. May be
        pressed repeatedly: one request → many ใบขอเบิก (ADR-0010)."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_("สร้างใบขอเบิกได้เฉพาะคำขอที่ได้รับอนุมัติแล้ว"))
        # Only the reference rides in the context — every default_* key would
        # stay on the form and leak into whatever its buttons create. The
        # header is filled from the request server-side (create) and on the
        # form (onchange).
        return {
            "type": "ir.actions.act_window",
            "name": _("ใบขอเบิก"),
            "res_model": "disbursement.request",
            "view_mode": "form",
            "target": "current",
            "context": {"default_approval_request_id": self.id},
        }

    def action_view_disbursement_request(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("ใบขอเบิก"),
            "res_model": "disbursement.request",
            "target": "current",
        }
        if len(self.disbursement_request_ids) == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.disbursement_request_ids.id
        else:
            action["view_mode"] = "tree,form"
            action["domain"] = [("id", "in", self.disbursement_request_ids.ids)]
        return action

    # -- closing -------------------------------------------------------------
    def _check_disbursement_user(self):
        if not self.env.user.has_group("disbursement.group_disbursement_user"):
            raise UserError(_("เฉพาะเจ้าหน้าที่การเงินเท่านั้น"))

    def action_close_disbursement(self):
        """ปิดคำขอ: no more ใบขอเบิก. A request that reserved its own budget
        returns its Remaining (ส่งคืนเงินเหลือจ่าย); one drawing a shared
        reservation returns nothing — the leftover stays with its owner.
        Finance may not write the request: sudo after the role check."""
        self._check_disbursement_user()
        for record in self.sudo():
            if record.state != "approved":
                raise UserError(_("ปิดได้เฉพาะคำขอที่ได้รับอนุมัติแล้ว"))
            if record.currency_id.compare_amounts(record.in_progress_amount, 0):
                raise UserError(
                    _(
                        "ยังมีใบขอเบิกอยู่ระหว่างเบิก %s — รอให้ตัดงบหรือยกเลิกก่อน"
                        "จึงจะปิดคำขอได้"
                    )
                    % record._money(record.in_progress_amount)
                )
            amount = max(record.remaining_amount, 0.0)
            returned = record._give_back_leftover(amount)
            record.write(
                {
                    "state": "done",
                    "closed_amount": amount,
                    "leftover_returned_amount": returned,
                }
            )
            record.message_post(
                body=_("ปิดคำขอ — ส่งคืนเงินเหลือจ่าย %s") % record._money(returned)
                if returned
                else _("ปิดคำขอ")
            )
        return True

    def action_reopen_disbursement(self):
        """เปิดคำขอกลับ (finance manager), only while nothing was returned:
        returned money is back in the pool and cannot simply be taken again."""
        if not self.env.user.has_group("disbursement.group_disbursement_manager"):
            raise UserError(_("เฉพาะผู้จัดการการเงินเท่านั้น"))
        for record in self.sudo():
            if record.state != "done":
                raise UserError(_("เปิดกลับได้เฉพาะคำขอที่เสร็จสิ้นแล้ว"))
            if record.leftover_returned_amount:
                raise UserError(
                    _(
                        "เปิดกลับไม่ได้ เพราะส่งคืนเงินเหลือจ่ายไปแล้ว %s — "
                        "ยื่นใบขออนุมัติใหม่แทน"
                    )
                    % record._money(record.leftover_returned_amount)
                )
            record.write({"state": "approved", "closed_amount": 0.0})
        return True

    def _give_back_leftover(self, amount):
        """Return ``amount`` of this request's own reservation to the budget
        (ส่งคืนเงินเหลือจ่าย) and say how much went back. A request drawing a
        shared reservation (project, procurement plan) returns nothing: the
        leftover stays with the reservation's owner."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        if (
            not commitment
            or self.reservation_commitment_id
            or self.currency_id.compare_amounts(amount, 0) <= 0
        ):
            return 0.0
        amount = min(amount, commitment.available_to_obligate)
        if commitment._return_leftover(
            source=self,
            name=_("ส่งคืนเงินเหลือจ่าย %s") % self.name,
            amount=amount,
        ):
            return amount
        return 0.0

    def _disbursement_sync_close(self):
        """Keep the close in step with the ใบขอเบิก: an open request closes by
        itself once fully disbursed; a closed one gives back, at once, money a
        cancelled ใบขอเบิก freed — so a Completed request always reads zero."""
        for record in self:
            currency = record.currency_id
            if record.state == "approved":
                if (
                    currency.compare_amounts(record.disbursed_amount, 0) > 0
                    and not currency.compare_amounts(record.in_progress_amount, 0)
                    and not currency.compare_amounts(record.remaining_amount, 0)
                ):
                    record.state = "done"
                    record.message_post(
                        body=_("เบิกจ่ายครบยอดอนุมัติ — ปิดคำขออัตโนมัติ")
                    )
            elif (
                record.state == "done"
                and currency.compare_amounts(record.remaining_amount, 0) > 0
            ):
                freed = record.remaining_amount
                returned = record._give_back_leftover(freed)
                record.write(
                    {
                        "closed_amount": record.closed_amount + freed,
                        "leftover_returned_amount": (
                            record.leftover_returned_amount + returned
                        ),
                    }
                )
                record.message_post(
                    body=_(
                        "ใบขอเบิกที่ตัดงบแล้วถูกยกเลิกหลังปิดคำขอ — ส่งคืนเงินเหลือจ่าย"
                        "เพิ่ม %s"
                    )
                    % record._money(returned)
                    if returned
                    else _(
                        "ใบขอเบิกที่ตัดงบแล้วถูกยกเลิกหลังปิดคำขอ — ยอด %s "
                        "กลับไปที่ใบจองร่วม"
                    )
                    % record._money(freed)
                )

    def action_cancel(self):
        # Rejecting a request still drawn by ใบขอเบิก would release the
        # reservation they draw down.
        for record in self:
            if record._active_disbursements():
                raise UserError(
                    _("ยกเลิกไม่ได้ เนื่องจากมีใบขอเบิกที่ยังไม่ถูกยกเลิก")
                )
        return super().action_cancel()
