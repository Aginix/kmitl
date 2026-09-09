# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "budget.commitment.mixin", "analytic.mixin"]

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        readonly=True,
        copy=False,
        help="Related budget commitment for this purchase request",
    )

    budget_commitment_state = fields.Selection(
        related="budget_commitment_id.state",
        string="สถานะใบจอง",
        readonly=True,
        help=(
            "ใช้ในฟอร์มเพื่อแยก 'มีใบจองที่ยังใช้งานอยู่' ออกจาก 'ใบจองถูกยกเลิกแล้ว' "
            "— การยกเลิกใบจองไม่ล้างค่า budget_commitment_id จึงต้องดูสถานะประกอบ"
        ),
    )
    budget_selection_mode = fields.Selection(
        selection=[
            ("normal", "ใช้เงินจากแผน (จองงบใหม่)"),
        ],
        string="วิธีเลือกงบประมาณ",
        default="normal",
        copy=False,
        help=(
            "เลือกว่าจะจองงบใหม่โดยเลือกมิติจากผังงบประมาณ "
            "หรือหยิบใบจองงบประมาณที่มีอยู่ไปใช้ (ตัวเลือกเพิ่มเติมจากโมดูลเสริม)"
        ),
    )
    reservation_commitment_id = fields.Many2one(
        "budget.commitment",
        string="ใบจองงบประมาณ",
        domain=lambda self: self._domain_reservation_commitment_id(),
        copy=False,
        tracking=True,
        help=(
            "เลือกใบจองงบประมาณที่มีอยู่แล้วเพื่อหยิบไปใช้ (draw down) แทนการจองใหม่ "
            "— เอกสารจะสืบทอดรหัสงบ/มิติ/ปีงบจากใบจองแบบล็อก และไม่จองซ้ำ. "
            "ใช้เมื่อเลือกวิธี 'หยิบจากใบจองงบประมาณที่มีอยู่'."
        ),
    )

    def _domain_reservation_commitment_id(self):
        """Reservations this document may draw down (phase-1 dropdown).

        Any reserved/in-progress commitment with obligable headroom, restricted to
        purchasable, product-backed budget codes — the same purchase_ok + product
        gate as the ``budget_account_id`` selector, so the dropdown only offers
        reservations this PR can actually draw — and to this request's own fiscal
        year, since drawing one adopts its ปีงบ (ADR-0010): offering another year's
        slip would silently flip the request's year. OU visibility is already
        enforced by the record rules (owner or beneficiary unit — ADR-0011).
        """
        return [
            ("state", "in", ("reserved", "partial")),
            ("available_to_obligate", ">", 0),
            ("account_id.purchase_ok", "=", True),
            ("account_id.product_id", "!=", False),
            ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
        ] + self._reservation_commitment_mode_domain()

    def _reservation_commitment_mode_domain(self):
        """Per-mode extension point for the ใบจองงบประมาณ picker domain.

        Base ships only the ``normal`` mode (no reservation picker). Bridge
        modules adding a mode override this to scope the picker to their own
        commitments (e.g. ``account_id.is_project`` / ``account_id.procurement_plan``)."""
        return []

    reservation_commitment_domain = fields.Binary(
        compute="_compute_reservation_commitment_domain",
        help=(
            "Record-aware domain for the ใบจองงบประมาณ dropdown. A static field "
            "domain cannot see this request's own account_fiscal_year_id, so the "
            "year filter is applied through this computed domain instead."
        ),
    )

    @api.depends("account_fiscal_year_id", "budget_selection_mode")
    def _compute_reservation_commitment_domain(self):
        for rec in self:
            rec.reservation_commitment_domain = rec._domain_reservation_commitment_id()

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=lambda self: self._domain_budget_account_id(),
        help="Budget account to be used for commitment",
        store=True,
        tracking=True,
        copy=True,
        readonly=False,
    )

    def _domain_budget_account_id(self):
        return [("purchase_ok", "=", True), ("product_id", "!=", False)]

    def _reservation_account_domain(self):
        # Only purchasable, product-backed budget codes are selectable for a PR,
        # matching the budget_account_id field domain — so the picker cannot
        # offer (nor apply_reservation_selection write) an account the PR would
        # reject or that would leave its lines product-less.
        return super()._reservation_account_domain() + self._domain_budget_account_id()

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        copy=True,
        readonly=False,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    is_budget_editable = fields.Boolean(compute="_compute_is_budget_editable")

    hide_reserve_budget_button = fields.Boolean(
        compute="_compute_hide_reserve_budget_button"
    )

    product_id = fields.Many2one(related=False, readonly=False)

    @api.depends(
        "state",
        "budget_commitment_id",
        "budget_commitment_id.state",
    )
    def _compute_is_budget_editable(self):
        # Means "budget selection is still open on this request", which is also
        # exactly when a reservation may be picked — so the reservation field
        # rides on this rather than re-listing states (purchase.request draws its
        # states from four modules, and three of them override this compute).
        # Drawing an existing reservation does not close selection: the user must
        # be able to un-pick. The chart picker is hidden view-side while a
        # reservation is picked, since dimensions then come from it.
        can_edit = self.env.user.has_group("budget.group_budget_commitment")
        for rec in self:
            if rec.state in ("to_verify", "to_approve") and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.is_budget_editable = can_edit
            else:
                rec.is_budget_editable = rec.is_editable

    @api.depends("state", "budget_commitment_id")
    def _compute_hide_reserve_budget_button(self):
        for rec in self:
            if rec.state in ("to_approve") and (
                rec.budget_commitment_id.state == "cancel"
                or not rec.budget_commitment_id
            ):
                rec.hide_reserve_budget_button = False
            else:
                rec.hide_reserve_budget_button = True

    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("sources")

    def action_view_budget_dashboard(self):
        self.ensure_one()
        root = self.budget_account_id
        while root.parent_id:
            root = root.parent_id
        return {
            "type": "ir.actions.client",
            "tag": "budget_dashboard",
            "name": "สถานะงบประมาณ",
            "target": "new",
            "context": {
                "default_fiscal_year_id": self.account_fiscal_year_id.id or False,
                "default_root_account_id": root.id if root else False,
                "default_department_analytic_id": self.department_analytic_id.id or False,
                "default_source_analytic_id": self.source_analytic_id.id or False,
                "default_fund_analytic_id": self.fund_analytic_id.id or False,
                "default_activity_analytic_id": self.activity_analytic_id.id or False,
            },
        }

    def action_open_budget_commitment(self):
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError("ยังไม่มี Budget Commitment สำหรับเอกสารนี้")

        return {
            "type": "ir.actions.act_window",
            "name": "Budget Commitment",
            "res_model": "budget.commitment",
            "view_mode": "form",
            "res_id": self.budget_commitment_id.id,
            "target": "current",
        }

    def _get_budget_commitment_extra_kwargs(self):
        """Extra kwargs forwarded to _create_budget_commitment().
        Override in bridge modules to inject e.g. operating_unit_id."""
        return {}

    def _get_commitment_title(self):
        """นำเลขที่เอกสาร พ.1 ไปไว้ในชื่อรายการจอง (ชื่อรายการจอง) ของใบจองที่ พ.1 สร้าง.

        ทุกที่ที่โชว์ใบจองใช้ ``display_name`` = ``BCxxxx - <ชื่อรายการจอง>`` — เลขที่ พ.1
        เดิมอยู่แค่ในช่อง ``ref`` ซึ่งไม่ปรากฏตรงนั้น จึง prefix เลขที่ไว้หน้าชื่อรายการเดิม
        เพื่อให้สืบย้อนกลับไปยัง พ.1 ต้นทางได้จากตัวรายการ."""
        self.ensure_one()
        base = super()._get_commitment_title()
        if self.name and base and base != self.name:
            return "[%s] %s" % (self.name, base)
        return self.name or base

    def action_reserve_budget(self):
        """Reserve budget: either draw an existing reservation or reserve anew."""
        self.ensure_one()

        # Draw-down mode: the user picked an existing ใบจองงบประมาณ. Adopt it
        # instead of creating a new commitment (ADR-0010) — presence of the pick
        # is the sole discriminator, no extra flag.
        if self.reservation_commitment_id:
            return self._action_draw_from_reservation()

        # Chose a draw-down mode but picked nothing: say so, instead of falling
        # through to reserve-new against the dimensions the mode switch cleared.
        if self.budget_selection_mode != "normal":
            raise UserError(_("กรุณาเลือกใบจองงบประมาณที่ต้องการหยิบไปใช้"))

        amount = sum(self.line_ids.mapped("estimated_cost"))

        # ปีงบยึดตามเอกสาร: check/reserve against this request's own fiscal year
        # (account_fiscal_year_id), not today() — otherwise a request whose FY differs
        # from today is checked against the wrong year.
        check_result = self._check_budget_availability(
            amount=amount,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
            account_fiscal_year_id=self.account_fiscal_year_id.id,
        )

        if not check_result["is_sufficient"]:
            raise UserError(
                _("Cannot reserve budget due to insufficient funds: %s")
                % check_result["message"]
            )

        try:
            commitment = self._create_budget_commitment(
                amount=amount,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Purchase Request: {self.name}",
                auto_reserve=True,
                account_fiscal_year_id=self.account_fiscal_year_id.id,
                **self._get_budget_commitment_extra_kwargs(),
            )
            self.message_post(
                body=_("Budget reserved: %s for amount %s") % (commitment.name, amount)
            )
            self.button_to_submit()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))

    def _action_draw_from_reservation(self):
        """Draw down an existing reservation (ใบจองงบประมาณ) instead of reserving.

        Adopts the reservation's budget code, fiscal year and full dimension
        distribution — locked onto the request and its lines — links it as the
        request's commitment, and advances the request exactly like the
        reserve-new path. No new reservation and no availability re-check: the
        money is already locked; obligate/consume happen downstream at the
        disbursement (ADR-0010)."""
        self.ensure_one()
        commitment = self.reservation_commitment_id
        if commitment.state not in ("reserved", "partial"):
            raise UserError(
                _("ใบจองงบประมาณ %s ไม่อยู่ในสถานะที่หยิบไปใช้ได้") % commitment.name
            )
        self._check_drawable_commitment(commitment)
        self.write(
            {
                "budget_commitment_id": commitment.id,
                "budget_account_id": commitment.account_id.id,
                "account_fiscal_year_id": commitment.account_fiscal_year_id.id,
                "analytic_distribution": commitment.analytic_distribution or False,
            }
        )
        if self.line_ids and commitment.analytic_distribution:
            self.line_ids.write(
                {"analytic_distribution": commitment.analytic_distribution}
            )
        self._apply_budget_account_product()
        self.message_post(
            body=_("หยิบใบจองงบประมาณ %s มาใช้ (draw down)") % commitment.name
        )
        self.button_to_submit()
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
            "context": self.env.context,
        }

    def _check_drawable_commitment(self, commitment):
        """Raise if this document may not draw ``commitment``.

        Base blocks any budget code the request could not itself select
        (purchasable, product-backed — draw-down writes budget_account_id
        directly, bypassing the UI-only field domain). Plan/project bridges
        extend this to block their own shared commitments, which are drawn only
        through their dedicated create-from-source flow (ADR-0006/0007).
        """
        if not self.env["budget.account"].search_count(
            self._reservation_account_domain()
            + [("id", "=", commitment.account_id.id)]
        ):
            raise UserError(
                _("รหัสงบประมาณของใบจองที่เลือกไม่สามารถใช้กับเอกสารนี้ได้")
            )
        return True

    @api.onchange("reservation_commitment_id")
    def _onchange_reservation_commitment_id(self):
        """Preview the picked reservation's budget code + fiscal year on the live
        form. The dimension distribution is written server-side on draw-down, not
        here — re-assigning analytic_distribution in an onchange makes its no-op
        compute wipe it on the unsaved record."""
        commitment = self.reservation_commitment_id
        if commitment:
            self.budget_account_id = commitment.account_id.id
            self.account_fiscal_year_id = commitment.account_fiscal_year_id.id

    @api.onchange("account_fiscal_year_id")
    def _onchange_account_fiscal_year_id(self):
        """เปลี่ยนปีงบ = ใบจองที่หยิบไว้ (คนละปีงบ) ใช้กับเอกสารนี้ไม่ได้แล้ว → ล้างทิ้ง.

        เทียบกับปีงบของใบจองเอง ไม่ใช่ล้างทุกครั้งที่ปีงบเปลี่ยน เพราะการหยิบใบจอง
        (``_onchange_reservation_commitment_id``) ตั้งปีงบ = ปีงบของใบจองอยู่แล้ว ถ้าล้าง
        ดื้อๆ การหยิบจะล้างตัวเองทันทีในรอบ onchange เดียวกัน."""
        if (
            self.reservation_commitment_id
            and self.reservation_commitment_id.account_fiscal_year_id
            != self.account_fiscal_year_id
        ):
            self.reservation_commitment_id = False

    @api.onchange("budget_selection_mode")
    def _onchange_budget_selection_mode(self):
        """Start budget selection fresh whenever the mode changes.

        ``budget_selection_mode`` is a **UI affordance only** — the server still
        keys draw-down off the presence of ``reservation_commitment_id``
        (ADR-0010), never off this field. Clear both the reservation pick and the
        accounting dimensions so nothing carries over from the previous mode: in
        particular, switching back to ``normal`` after picking a ใบจองงบประมาณ
        must not leave that commitment's dimensions on the form, or the user
        could reserve new budget against them.
        """
        self.reservation_commitment_id = False
        self.budget_account_id = False
        self.analytic_distribution = False

    def _cancel_budget_commitment(self):
        """A drawn reservation belongs to its owner, never to this request — detach
        instead of cancelling when this PR drew an existing reservation (ADR-0010)."""
        self.ensure_one()
        if self.reservation_commitment_id:
            self.write(
                {"budget_commitment_id": False, "reservation_commitment_id": False}
            )
            return True
        return super()._cancel_budget_commitment()

    def _compute_to_approve_allowed(self):
        super()._compute_to_approve_allowed()
        for rec in self:
            rec.to_approve_allowed = rec.state == "to_submit" and any(
                not line.cancelled and line.product_qty for line in rec.line_ids
            )

    def button_draft(self):
        for record in self:
            if record.budget_commitment_id:
                if record._release_commitment_on_draft():
                    try:
                        name = record.budget_commitment_id.name
                        record._cancel_budget_commitment()
                        record.message_post(
                            body=_("Budget commitment %s has been cancelled") % name
                        )
                    except UserError as e:
                        record.message_post(
                            body=_("Warning: Could not cancel budget commitment: %s")
                            % str(e)
                        )
                record.write({"verified_by": "", "date_verified": False})

        return super().button_draft()

    def _release_commitment_on_draft(self):
        """Whether ดึงกลับ (Reset) should release this request's budget commitment.

        Base: yes — a normal/own commitment is cancelled on Reset so the budget can
        be re-selected. Project/plan bridges keep their shared commitment on Reset
        (recall to edit the request, not to give up the project/plan budget) and
        release it only on ยกเลิก (Cancel)."""
        self.ensure_one()
        return True

    def button_rejected(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(
                        body=_("Budget commitment %s has been cancelled")
                        % record.budget_commitment_id.name
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

        return super().button_rejected()

    def button_cancel(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(
                        body=_("Budget commitment %s has been cancelled")
                        % record.budget_commitment_id.name
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

        return super().button_cancel()

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all order lines"""
        if self.analytic_distribution:
            self.line_ids.update({"analytic_distribution": self.analytic_distribution})

    def write(self, vals):
        result = super().write(vals)
        if "budget_account_id" in vals:
            for rec in self:
                product = rec.budget_account_id.product_id
                if product and rec.line_ids:
                    rec.line_ids.write({"product_id": product.id})
        return result

    @api.onchange("budget_account_id")
    def _onchange_budget_account_id(self):
        self._apply_budget_account_product()

    def _apply_budget_account_product(self):
        """Set the product from the budget account and ensure a PR line.

        Shared by the budget_account_id onchange and the reservation picker:
        the picker writes via ORM (no onchange fires), so it calls this directly
        to keep the PR line in sync with the chosen budget code.
        """
        product_id = self.budget_account_id.product_id
        if not product_id:
            return
        self.product_id = product_id.id
        if self.line_ids:
            self.line_ids.write({"product_id": product_id.id})
        else:
            default_price = self.env.context.get("default_price_unit", 0)
            self.line_ids = [
                Command.create(
                    {
                        "product_id": product_id.id,
                        "name": product_id.display_name,
                        "product_uom_id": product_id.uom_id.id,
                        "price_unit": getattr(self, "procurement_plan_id", False)
                        and self.procurement_plan_id.total_price
                        or default_price,
                        "product_qty": 1.0,
                    }
                )
            ]

    def apply_reservation_selection(self, selections, dims=None):
        """Picker write-back: set the budget code + dimensions, then sync the
        product line (the manual onchange does not fire on an ORM write)."""
        res = super().apply_reservation_selection(selections, dims=dims)
        self._apply_budget_account_product()
        return res
