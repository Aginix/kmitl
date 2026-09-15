# -*- coding: utf-8 -*-
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class PurchaseContract(models.Model):
    _name = "purchase.contract"
    _description = "Purchase Contract Revision"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "purchase_id, revision_number"

    purchase_id = fields.Many2one(
        "purchase.order",
        string="Purchase Order",
        required=True,
        ondelete="cascade",
        index=True,
    )
    revision_number = fields.Integer(
        string="Revision",
        default=0,
        help="0 = original snapshot at PO confirm; 1+ = user-initiated amendments.",
    )
    revision_display = fields.Char(
        string="Revision Label",
        compute="_compute_revision_display",
        store=True,
    )
    is_original = fields.Boolean(
        compute="_compute_is_original",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("applied", "Applied"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    # --- Mutable contract fields (snapshot per revision) ---
    fines_rate = fields.Monetary(string="Daily Fine Rate")
    supervision_cost = fields.Monetary(string="Supervision Cost")
    date_order_date = fields.Date(string="Contract Signing Date")
    work_start = fields.Date(string="Work Start Date")
    extension_days = fields.Integer(
        string="Extension Days (this revision)",
        default=0,
        help="Days added on top of the previous work_end. Cumulative across "
        "revisions is exposed on the PO's contract_period_days.",
    )
    work_end = fields.Date(
        string="Work End Date",
        compute="_compute_work_end",
        store=True,
    )

    # Snapshot O2M
    contract_line_ids = fields.One2many(
        "purchase.contract.line",
        "contract_id",
        string="Lines Snapshot",
        copy=True,
    )
    contract_invoice_plan_ids = fields.One2many(
        "purchase.contract.invoice.plan",
        "contract_id",
        string="Invoice Plan Snapshot",
        copy=True,
    )

    # Committee snapshots (M2M to hr.employee for now; may be extended to a
    # dedicated line model in a follow-up if committee roles need to be tracked)
    work_acceptance_committee_ids = fields.Many2many(
        "hr.employee",
        "purchase_contract_wa_committee_rel",
        "contract_id",
        "employee_id",
        string="Work Acceptance Committee",
    )
    work_supervisor_ids = fields.Many2many(
        "hr.employee",
        "purchase_contract_supervisor_rel",
        "contract_id",
        "employee_id",
        string="Work Supervisors",
    )

    approval_attachment_ids = fields.Many2many(
        "ir.attachment",
        "purchase_contract_attachment_rel",
        "contract_id",
        "attachment_id",
        string="Approval Documents",
        help="External approval evidence. At least one file is required before "
        "the revision can be applied.",
    )

    amount_total = fields.Monetary(
        compute="_compute_amount_total",
        store=True,
    )
    currency_id = fields.Many2one(
        related="purchase_id.currency_id",
        store=True,
        readonly=True,
    )

    applied_by = fields.Many2one("res.users", readonly=True, copy=False)
    applied_date = fields.Datetime(readonly=True, copy=False)

    case = fields.Selection(
        [
            ("single", "Single Payment (no งวด)"),
            ("phased_none_disbursed", "Phased — nothing disbursed"),
            ("phased_partial_disbursed", "Phased — partially disbursed"),
        ],
        compute="_compute_case",
    )

    # ------------------------------------------------------------------
    # Concurrency: only one draft revision per PO
    # ------------------------------------------------------------------
    @api.constrains("state", "purchase_id")
    def _check_one_draft_per_po(self):
        for rec in self:
            if rec.state != "draft":
                continue
            others = rec.purchase_id.contract_ids.filtered(
                lambda r: r.state == "draft" and r.id != rec.id
            )
            if others:
                raise ValidationError(
                    _(
                        "PO %s มี revision draft ค้างอยู่แล้ว (ครั้งที่ %s) — ต้อง apply "
                        "หรือ cancel ก่อนสร้างใหม่"
                    )
                    % (rec.purchase_id.name, others[:1].revision_number)
                )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("revision_number")
    def _compute_revision_display(self):
        for rec in self:
            if rec.revision_number == 0:
                rec.revision_display = _("ต้นฉบับ")
            else:
                rec.revision_display = _("ครั้งที่ %s") % rec.revision_number

    @api.depends("revision_number")
    def _compute_is_original(self):
        for rec in self:
            rec.is_original = rec.revision_number == 0

    @api.depends("contract_line_ids.subtotal")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.contract_line_ids.mapped("subtotal"))

    @api.depends(
        "work_start",
        "extension_days",
        "purchase_id.contract_ids.extension_days",
        "purchase_id.contract_ids.state",
    )
    def _compute_work_end(self):
        """work_end = work_start + Σextension_days of applied prior revs + this rev's extension_days."""
        for rec in self:
            if not rec.work_start:
                rec.work_end = False
                continue
            # extensions accumulated on prior applied revisions (excluding self)
            prior = rec.purchase_id.contract_ids.filtered(
                lambda r: r.state == "applied"
                and r.revision_number < rec.revision_number
                and r.id != rec.id
            )
            base_days = sum(prior.mapped("extension_days"))
            total = base_days + (rec.extension_days or 0)
            rec.work_end = fields.Date.add(rec.work_start, days=total)

    # ------------------------------------------------------------------
    # Snapshot helpers — populate a fresh contract from a PO or another rev
    # ------------------------------------------------------------------
    def _snapshot_lines_from_po(self, po):
        """Clone po.order_line into contract_line_ids on self."""
        self.ensure_one()
        Line = self.env["purchase.contract.line"]
        for seq, ol in enumerate(po.order_line, start=1):
            Line.create(
                {
                    "contract_id": self.id,
                    "sequence": ol.sequence or seq,
                    "product_id": ol.product_id.id,
                    "name": ol.name,
                    "product_qty": ol.product_qty,
                    "product_uom": ol.product_uom.id,
                    "price_unit": ol.price_unit,
                    "taxes_id": [(6, 0, ol.taxes_id.ids)],
                    "analytic_distribution": ol.analytic_distribution,
                    "source_order_line_id": ol.id,
                }
            )

    def _snapshot_invoice_plan_from_po(self, po):
        """Clone po.invoice_plan_ids into contract_invoice_plan_ids on self."""
        self.ensure_one()
        Plan = self.env["purchase.contract.invoice.plan"]
        for ip in po.invoice_plan_ids:
            Plan.create(
                {
                    "contract_id": self.id,
                    "installment": ip.installment,
                    "duration_days": ip.duration_days,
                    "plan_date": ip.plan_date,
                    "amount": ip.amount,
                    "percent": ip.percent,
                    "source_invoice_plan_id": ip.id,
                }
            )

    def _snapshot_committees_from_po(self, po):
        """Snapshot committee employee IDs (M2M) from the PO."""
        self.ensure_one()
        wa_employees = po.work_acceptance_committee_ids.mapped("employee_id")
        ws_employees = po.work_supervisor_ids.mapped("employee_id")
        self.write(
            {
                "work_acceptance_committee_ids": [(6, 0, wa_employees.ids)],
                "work_supervisor_ids": [(6, 0, ws_employees.ids)],
            }
        )

    def _clone_lines_from(self, other):
        """Deep-copy contract_line_ids from another contract into self."""
        self.ensure_one()
        Line = self.env["purchase.contract.line"]
        for src in other.contract_line_ids:
            Line.create(
                {
                    "contract_id": self.id,
                    "sequence": src.sequence,
                    "product_id": src.product_id.id,
                    "name": src.name,
                    "product_qty": src.product_qty,
                    "product_uom": src.product_uom.id,
                    "price_unit": src.price_unit,
                    "taxes_id": [(6, 0, src.taxes_id.ids)],
                    "analytic_distribution": src.analytic_distribution,
                    "source_order_line_id": src.source_order_line_id.id,
                }
            )

    def _clone_invoice_plan_from(self, other):
        """Deep-copy contract_invoice_plan_ids from another contract into self."""
        self.ensure_one()
        Plan = self.env["purchase.contract.invoice.plan"]
        for src in other.contract_invoice_plan_ids:
            Plan.create(
                {
                    "contract_id": self.id,
                    "installment": src.installment,
                    "duration_days": src.duration_days,
                    "plan_date": src.plan_date,
                    "amount": src.amount,
                    "percent": src.percent,
                    "source_invoice_plan_id": src.source_invoice_plan_id.id,
                }
            )

    def _clone_committees_from(self, other):
        self.ensure_one()
        self.write(
            {
                "work_acceptance_committee_ids": [
                    (6, 0, other.work_acceptance_committee_ids.ids)
                ],
                "work_supervisor_ids": [(6, 0, other.work_supervisor_ids.ids)],
            }
        )

    # ------------------------------------------------------------------
    # Case detection
    # ------------------------------------------------------------------
    @api.depends(
        "purchase_id.invoice_plan_ids",
        "contract_invoice_plan_ids.is_frozen",
    )
    def _compute_case(self):
        for rec in self:
            po = rec.purchase_id
            if not po.invoice_plan_ids:
                rec.case = "single"
            elif rec.contract_invoice_plan_ids.filtered("is_frozen"):
                rec.case = "phased_partial_disbursed"
            else:
                rec.case = "phased_none_disbursed"

    # ------------------------------------------------------------------
    # Hard validation — invoked from action_apply
    # ------------------------------------------------------------------
    def _check_can_apply(self):
        self.ensure_one()

        # (1) Attachment gate
        if not self.approval_attachment_ids:
            raise UserError(
                _("กรุณาแนบเอกสารอนุมัติอย่างน้อย 1 ไฟล์ก่อนบันทึกการแก้ไข")
            )

        # (2) Line values must be non-zero / non-empty
        if not self.contract_line_ids:
            raise UserError(_("ต้องมีรายการสินค้าอย่างน้อย 1 รายการ"))
        for line in self.contract_line_ids:
            if not line.product_qty or not line.price_unit:
                raise UserError(
                    _(
                        "รายการ '%s' มีจำนวนหรือราคาต่อหน่วยเป็น 0 หรือว่าง — "
                        "กรุณากรอกให้ครบ"
                    )
                    % (line.name or line.product_id.display_name)
                )

        prev = self.purchase_id.current_contract_id
        if not prev:
            raise UserError(
                _("PO นี้ยังไม่มีสัญญาต้นฉบับ — ไม่สามารถแก้ไขได้")
            )

        # (3) analytic_distribution exact-match against prev revision
        prev_distributions = {
            self._normalise_distribution(l.analytic_distribution)
            for l in prev.contract_line_ids
        }
        for line in self.contract_line_ids:
            norm = self._normalise_distribution(line.analytic_distribution)
            if norm not in prev_distributions:
                raise UserError(
                    _(
                        "รายการ '%s' มีรหัสงบประมาณ (analytic_distribution) "
                        "ไม่ตรงกับสัญญาเดิม — ห้ามย้ายงบ"
                    )
                    % (line.name or line.product_id.display_name)
                )

        # (4) Total must not exceed previous revision
        if (
            self._money_compare(self.amount_total, prev.amount_total) > 0
        ):
            raise UserError(
                _(
                    "มูลค่าสัญญาใหม่ (%s) สูงกว่าสัญญาเดิม (%s) — ห้ามเพิ่มมูลค่า"
                )
                % (self.amount_total, prev.amount_total)
            )

        # (5) Phased-specific rules
        if self.case == "phased_partial_disbursed":
            frozen = self.contract_invoice_plan_ids.filtered("is_frozen")
            unfrozen = self.contract_invoice_plan_ids - frozen
            frozen_total = sum(frozen.mapped("amount"))

            # (5a) Total must be ≥ sum of frozen งวด
            if self._money_compare(self.amount_total, frozen_total) < 0:
                raise UserError(
                    _(
                        "มูลค่าใหม่ (%s) ต่ำกว่ายอดรวมงวดที่มีใบเบิกแล้ว (%s)"
                    )
                    % (self.amount_total, frozen_total)
                )

            # (5b) Invoice plan must balance to amount_total
            plan_total = sum(self.contract_invoice_plan_ids.mapped("amount"))
            if self._money_compare(plan_total, self.amount_total) != 0:
                raise UserError(
                    _(
                        "ยอดรวมงวดงาน (%s) ต้องเท่ากับมูลค่าสัญญา (%s)"
                    )
                    % (plan_total, self.amount_total)
                )

            # (5c) Frozen rows must match prev exactly
            prev_by_source = {
                ip.source_invoice_plan_id.id: ip
                for ip in prev.contract_invoice_plan_ids
                if ip.source_invoice_plan_id
            }
            for row in frozen:
                prev_row = prev_by_source.get(row.source_invoice_plan_id.id)
                if not prev_row:
                    raise UserError(
                        _("พบงวดที่ frozen แต่ไม่มีต้นฉบับใน revision ก่อนหน้า")
                    )
                if (
                    self._money_compare(row.amount, prev_row.amount) != 0
                    or row.installment != prev_row.installment
                    or row.plan_date != prev_row.plan_date
                ):
                    raise UserError(
                        _(
                            "งวดที่ %s ตรวจรับแล้ว/มีใบเบิกแล้ว — ห้ามแก้ไข"
                        )
                        % row.installment
                    )

    # ------------------------------------------------------------------
    # Apply — write snapshot back to PO
    # ------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                _("Revision นี้ไม่ได้อยู่ในสถานะ draft — apply ไม่ได้")
            )
        self._check_can_apply()
        self._apply_to_purchase_order()
        self.write(
            {
                "state": "applied",
                "applied_by": self.env.uid,
                "applied_date": fields.Datetime.now(),
            }
        )
        self.message_post(
            body=_("บันทึกการแก้ไขสัญญา — %s (apply โดย %s)")
            % (self.revision_display, self.env.user.display_name)
        )
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("ยกเลิกได้เฉพาะ revision ที่ยังเป็น draft"))
        self.write({"state": "cancelled"})
        for rec in self:
            rec.message_post(body=_("ยกเลิก revision (draft → cancelled)"))
        return True

    def _apply_to_purchase_order(self):
        """Write the revision snapshot back onto purchase.order and its lines.

        Budget commitment is intentionally NOT touched: the original reserved
        amount stays locked even if the new total is lower.

        Committee sync is deferred — committee snapshots on the contract are
        display-only for now. See TODO in module README."""
        self.ensure_one()
        po = self.purchase_id

        # Total contract days = original rev0 base + Σ extension_days across
        # all applied revs + this rev's extension_days.
        rev0 = po.contract_ids.filtered(lambda r: r.revision_number == 0)[:1]
        rev0_period = rev0.contract_line_ids and (
            po.contract_period_days
            - sum(
                po.contract_ids.filtered(
                    lambda r: r.state == "applied"
                    and r.revision_number > 0
                ).mapped("extension_days")
            )
        ) or po.contract_period_days
        prior_extensions = sum(
            po.contract_ids.filtered(
                lambda r: r.state == "applied"
                and r.revision_number > 0
                and r.id != self.id
            ).mapped("extension_days")
        )
        new_period = rev0_period + prior_extensions + (self.extension_days or 0)

        po.write(
            {
                "fines_rate": self.fines_rate,
                "supervision_cost": self.supervision_cost,
                "date_order_date": self.date_order_date,
                "work_start": self.work_start,
                "contract_period_days": new_period,
            }
        )

        self._sync_order_lines_to_po()
        self._sync_invoice_plan_to_po()

    def _sync_order_lines_to_po(self):
        """Replace purchase.order.line to match contract_line_ids.

        Matches by source_order_line_id when present (in-place update);
        otherwise creates a new order line. Order lines that no longer have a
        matching contract line are unlinked."""
        self.ensure_one()
        po = self.purchase_id
        POL = self.env["purchase.order.line"]

        kept_source_ids = set()
        for cl in self.contract_line_ids:
            vals = {
                "product_id": cl.product_id.id,
                "name": cl.name,
                "product_qty": cl.product_qty,
                "product_uom": cl.product_uom.id
                or cl.product_id.uom_po_id.id,
                "price_unit": cl.price_unit,
                "taxes_id": [(6, 0, cl.taxes_id.ids)],
                "analytic_distribution": cl.analytic_distribution,
                "sequence": cl.sequence,
            }
            if cl.source_order_line_id:
                cl.source_order_line_id.write(vals)
                kept_source_ids.add(cl.source_order_line_id.id)
            else:
                new_line = POL.create({**vals, "order_id": po.id})
                cl.source_order_line_id = new_line.id
                kept_source_ids.add(new_line.id)

        # Unlink any live PO lines that this revision dropped. The base
        # ``@api.ondelete`` guard blocks deletion on confirmed POs; the
        # purchase_order_line override in this module honours our context
        # flag to allow deletion when triggered from an applied revision.
        to_remove = po.order_line.filtered(lambda l: l.id not in kept_source_ids)
        if to_remove:
            to_remove.with_context(from_contract_revision_apply=True).unlink()

    def _sync_invoice_plan_to_po(self):
        """Reconcile purchase.invoice.plan against contract_invoice_plan_ids.

        Frozen rows are matched by source and left untouched. Unfrozen live
        rows are updated in-place or created/unlinked to match the snapshot."""
        self.ensure_one()
        po = self.purchase_id
        Plan = self.env["purchase.invoice.plan"]

        kept_source_ids = set()
        for cip in self.contract_invoice_plan_ids:
            vals = {
                "installment": cip.installment,
                "duration_days": cip.duration_days,
                "plan_date": cip.plan_date,
                "amount": cip.amount,
                "percent": cip.percent,
            }
            if cip.source_invoice_plan_id:
                # Frozen rows would have been rejected at validation if they
                # changed; safe to write through.
                cip.source_invoice_plan_id.write(vals)
                kept_source_ids.add(cip.source_invoice_plan_id.id)
            else:
                new_plan = Plan.create({**vals, "purchase_id": po.id})
                cip.source_invoice_plan_id = new_plan.id
                kept_source_ids.add(new_plan.id)

        # Unlink live งวด not represented in the snapshot — but only unfrozen
        # ones (frozen must persist regardless).
        Disbursement = self.env["disbursement.request"].sudo()
        has_disbursement = bool(
            Disbursement.search_count([("purchase_id", "=", po.id)])
        )
        for ip in po.invoice_plan_ids:
            if ip.id in kept_source_ids:
                continue
            if has_disbursement and ip.invoiced:
                # Safety net — should have been prevented by validation
                continue
            ip.unlink()

    def _money_compare(self, a, b):
        """Compare two monetary values using the contract's currency precision."""
        self.ensure_one()
        precision = self.currency_id.decimal_places if self.currency_id else 2
        return float_compare(a or 0.0, b or 0.0, precision_digits=precision)

    # ------------------------------------------------------------------
    # Diff computation for the amendment report
    # ------------------------------------------------------------------
    def _previous_revision(self):
        """Return the immediately-preceding applied revision, if any."""
        self.ensure_one()
        priors = self.purchase_id.contract_ids.filtered(
            lambda r: r.state == "applied"
            and r.revision_number < self.revision_number
        ).sorted("revision_number")
        return priors[-1:] if priors else self.browse()

    def _prepare_report_data(self):
        """Structured payload consumed by the amendment report template."""
        self.ensure_one()
        prev = self._previous_revision()
        return {
            "contract": self,
            "prev": prev,
            "header_diff": self._diff_header(prev),
            "line_diff": self._diff_lines(prev),
            "plan_diff": self._diff_invoice_plan(prev),
            "committee_diff": self._diff_committees(prev),
        }

    def _diff_header(self, prev):
        self.ensure_one()
        fields_to_diff = [
            ("fines_rate", "ค่าปรับรายวัน"),
            ("supervision_cost", "ค่าใช้จ่ายในการควบคุมงาน"),
            ("date_order_date", "วันที่ลงนามสัญญา"),
            ("work_start", "วันที่เริ่มงาน"),
            ("extension_days", "จำนวนวันขยาย (ครั้งนี้)"),
            ("work_end", "กำหนดวันส่งมอบ"),
        ]
        rows = []
        for fname, label in fields_to_diff:
            old = prev[fname] if prev else None
            new = self[fname]
            if old != new:
                rows.append({"label": label, "old": old, "new": new})
        return rows

    def _diff_lines(self, prev):
        self.ensure_one()
        prev_by_source = {}
        if prev:
            for pl in prev.contract_line_ids:
                if pl.source_order_line_id:
                    prev_by_source[pl.source_order_line_id.id] = pl
        added, removed, changed = [], [], []
        seen_prev = set()
        for line in self.contract_line_ids:
            src = line.source_order_line_id.id
            prev_line = prev_by_source.get(src)
            if not prev_line:
                added.append(line)
                continue
            seen_prev.add(prev_line.id)
            if (
                line.product_qty != prev_line.product_qty
                or line.price_unit != prev_line.price_unit
            ):
                changed.append({"old": prev_line, "new": line})
        if prev:
            for pl in prev.contract_line_ids:
                if pl.id not in seen_prev and pl.source_order_line_id.id not in [
                    l.source_order_line_id.id for l in self.contract_line_ids
                ]:
                    removed.append(pl)
        return {"added": added, "removed": removed, "changed": changed}

    def _diff_invoice_plan(self, prev):
        self.ensure_one()
        prev_by_source = {}
        if prev:
            for pip in prev.contract_invoice_plan_ids:
                if pip.source_invoice_plan_id:
                    prev_by_source[pip.source_invoice_plan_id.id] = pip
        added, removed, changed = [], [], []
        for row in self.contract_invoice_plan_ids:
            prev_row = prev_by_source.get(row.source_invoice_plan_id.id)
            if not prev_row:
                added.append(row)
                continue
            if (
                row.amount != prev_row.amount
                or row.plan_date != prev_row.plan_date
                or row.installment != prev_row.installment
            ):
                changed.append({"old": prev_row, "new": row})
        if prev:
            current_sources = {
                r.source_invoice_plan_id.id for r in self.contract_invoice_plan_ids
            }
            for pip in prev.contract_invoice_plan_ids:
                if pip.source_invoice_plan_id.id not in current_sources:
                    removed.append(pip)
        return {"added": added, "removed": removed, "changed": changed}

    def _diff_committees(self, prev):
        self.ensure_one()
        result = {}
        for fname, label in [
            ("work_acceptance_committee_ids", "กรรมการตรวจรับ"),
            ("work_supervisor_ids", "ผู้ควบคุมงาน"),
        ]:
            new = self[fname]
            old = prev[fname] if prev else self.browse()
            result[fname] = {
                "label": label,
                "added": new - old,
                "removed": old - new,
                "kept": new & old,
            }
        return result

    @staticmethod
    def _normalise_distribution(distribution):
        """Return a hashable canonical form for analytic_distribution comparison."""
        if not distribution:
            return None
        # Odoo stores as {str(id): percent}; sort keys for deterministic order
        try:
            return json.dumps(distribution, sort_keys=True)
        except TypeError:
            return None
