import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import formatLang

_logger = logging.getLogger(__name__)


class KrisProjectAllocationLine(models.Model):
    _name = "kris.project.allocation.line"
    _description = "KRIS Project Allocation Line"
    _order = "sequence, id"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    item_id = fields.Many2one(
        comodel_name="kris.project.allocation.item",
        string="Allocator",
        required=True,
    )
    name = fields.Char(
        string="Allocator",
        related="item_id.name",
        store=True,
        readonly=True,
    )
    allocation_pct = fields.Float(
        string="Allocation %",
        digits=(5, 2),
        compute="_compute_allocation_pct",
        store=True,
    )
    estimated_amount = fields.Monetary(
        string="Estimated Amount (Baht)",
    )
    actual_amount = fields.Monetary(
        string="Actual Amount (Baht)",
        compute="_compute_actual_amount",
        store=True,
    )
    installment_allocation_ids = fields.One2many(
        comodel_name="kris.project.installment.allocation",
        inverse_name="allocation_line_id",
        string="Installment allocation",
    )
    receipt_allocation_ids = fields.One2many(
        comodel_name="kris.project.receipt.allocation",
        inverse_name="allocation_line_id",
        string="Allocation based on revenue.",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.depends("estimated_amount", "project_id.maintenance_deduction_amount")
    def _compute_allocation_pct(self):
        for line in self:
            base = line.project_id.maintenance_deduction_amount
            if base:
                line.allocation_pct = line.estimated_amount / base * 100.0
            else:
                line.allocation_pct = 0.0

    @api.depends("receipt_allocation_ids.amount")
    def _compute_actual_amount(self):
        for line in self:
            line.actual_amount = sum(line.receipt_allocation_ids.mapped("amount"))

    @api.constrains("estimated_amount")
    def _check_estimated_amount_sum(self):
        for line in self:
            base = line.project_id.maintenance_deduction_amount
            if not base:
                continue
            total = sum(line.project_id.allocation_line_ids.mapped("estimated_amount"))
            if total > base + 1e-9:
                raise ValidationError(
                    _(
                        "ผลรวมประมาณการจัดสรรต้องไม่เกินมูลค่าหักค่าบำรุง (%.2f บาท)"
                    )
                    % base
                )

    def _format_amount(self, amount):
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    _TRACKED_FIELDS = {"item_id", "estimated_amount"}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("skip_message_post"):
            for rec in records:
                if rec.project_id:
                    body = _("เพิ่มการจัดสรรรายได้: %s จำนวน %s") % (
                        rec.name,
                        rec._format_amount(rec.estimated_amount),
                    )
                    rec.project_id.message_post(
                        body=body, subtype_xmlid="mail.mt_note"
                    )
        return records

    def write(self, vals):
        tracked = set(vals) & self._TRACKED_FIELDS
        old_values = {}
        if tracked and not self.env.context.get("skip_message_post"):
            for rec in self:
                old_values[rec.id] = {f: rec[f] for f in tracked}
        result = super().write(vals)
        for rec in self:
            if rec.id not in old_values or not rec.project_id:
                continue
            changes = []
            for field_name, old_val in old_values[rec.id].items():
                new_val = rec[field_name]
                if old_val != new_val:
                    label = rec._fields[field_name].string
                    if field_name == "estimated_amount":
                        old_val = rec._format_amount(old_val)
                        new_val = rec._format_amount(new_val)
                    elif field_name == "item_id":
                        old_val = old_val.display_name or ""
                        new_val = new_val.display_name or ""
                    changes.append(
                        _("%(label)s: %(old)s → %(new)s")
                        % {"label": label, "old": old_val, "new": new_val}
                    )
            if changes:
                body = _("แก้ไขการจัดสรรรายได้ %s") % rec.name
                body += "<ul>%s</ul>" % "".join(
                    "<li>%s</li>" % c for c in changes
                )
                rec.project_id.message_post(
                    body=body, subtype_xmlid="mail.mt_note"
                )
        return result

    def unlink(self):
        messages = []
        if not self.env.context.get("skip_message_post"):
            for rec in self:
                if rec.project_id:
                    messages.append(
                        (rec.project_id, _("ลบการจัดสรรรายได้: %s") % rec.name)
                    )
        result = super().unlink()
        for project, body in messages:
            project.message_post(body=body, subtype_xmlid="mail.mt_note")
        return result
