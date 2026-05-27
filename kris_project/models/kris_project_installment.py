import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import formatLang

_logger = logging.getLogger(__name__)


class KrisProjectInstallment(models.Model):
    _name = "kris.project.installment"
    _description = "KRIS Project Installment"
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
    name = fields.Char(
        string="Installment",
        required=True,
    )
    amount = fields.Monetary(
        string="Amount Receive",
    )
    due_date = fields.Date(
        string="Date Due",
    )
    state = fields.Selection(
        selection=[
            ("pending", "รอรับเงิน"),
            ("received", "รับเงินแล้ว"),
        ],
        string="State",
        default="pending",
    )
    deduction_guarantee = fields.Monetary(
        string="Guarantee Deduction",
    )
    deduction_advance = fields.Monetary(
        string="Advance Deduction",
    )
    received_from_employer = fields.Monetary(
        string="Received From Client",
        compute="_compute_received_from_employer",
        store=True,
    )
    maintenance_fee = fields.Monetary(
        string="Maintenance Fee",
        compute="_compute_maintenance_fee",
        store=True,
    )
    extra_deduction = fields.Monetary(
        string="Extra Deduction",
    )
    extra_income = fields.Monetary(
        string="Extra Value",
    )
    amount_net = fields.Monetary(
        string="Net Amount",
        compute="_compute_amount_net",
        store=True,
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.installment.allocation",
        inverse_name="installment_id",
        string="Allocation",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project_id = res.get("project_id") or self.env.context.get("default_project_id")
        if project_id and "allocation_ids" in fields_list:
            project = self.env["kris.project"].browse(project_id)
            res["allocation_ids"] = [
                (0, 0, {"allocation_line_id": line.id, "amount": 0.0})
                for line in project.allocation_line_ids
            ]
        return res

    _TRACKED_FIELDS = {
        "name", "amount", "due_date", "deduction_guarantee",
        "deduction_advance", "extra_deduction", "extra_income",
    }

    def _format_amount(self, amount):
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    def _format_field_value(self, field_name, value):
        if field_name in (
            "amount", "deduction_guarantee", "deduction_advance",
            "extra_deduction", "extra_income",
        ):
            return self._format_amount(value or 0.0)
        if field_name == "due_date":
            return str(value) if value else ""
        return str(value) if value else ""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence") and vals.get("project_id"):
                project = self.env["kris.project"].browse(vals["project_id"])
                max_seq = max(project.installment_ids.mapped("sequence") or [0])
                vals["sequence"] = max_seq + 10
        records = super().create(vals_list)
        if not self.env.context.get("skip_message_post"):
            for rec in records:
                if rec.project_id:
                    body = _("เพิ่มงวดงาน: %s จำนวน %s") % (
                        rec.name,
                        rec._format_amount(rec.amount),
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
                    changes.append(
                        _("%(label)s: %(old)s → %(new)s")
                        % {
                            "label": label,
                            "old": rec._format_field_value(field_name, old_val),
                            "new": rec._format_field_value(field_name, new_val),
                        }
                    )
            if changes:
                body = _("แก้ไขงวดงาน %s") % rec.name
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
                        (rec.project_id, _("ลบงวดงาน: %s") % rec.name)
                    )
        result = super().unlink()
        for project, body in messages:
            project.message_post(body=body, subtype_xmlid="mail.mt_note")
        return result

    @api.depends("amount", "deduction_guarantee", "deduction_advance")
    def _compute_received_from_employer(self):
        for rec in self:
            rec.received_from_employer = (
                rec.amount - rec.deduction_guarantee - rec.deduction_advance
            )

    @api.constrains("extra_income", "project_id")
    def _check_extra_income_total(self):
        for rec in self:
            project = rec.project_id
            if not project:
                continue
            total_extra = sum(project.installment_ids.mapped("extra_income"))
            if total_extra > project.extra_value + 1e-9:
                raise ValidationError(
                    _(
                        "ยอดค่า Extra รวมทุกงวด (%.2f บาท) เกินจากยอดค่า Extra โครงการ (%.2f บาท)"
                    )
                    % (total_extra, project.extra_value)
                )

    @api.depends("allocation_ids.amount")
    def _compute_maintenance_fee(self):
        for rec in self:
            rec.maintenance_fee = sum(rec.allocation_ids.mapped("amount"))

    @api.depends("received_from_employer", "maintenance_fee", "extra_deduction", 'extra_income')
    def _compute_amount_net(self):
        for rec in self:
            rec.amount_net = (
                rec.received_from_employer - rec.maintenance_fee - rec.extra_deduction - rec.extra_income
            )
