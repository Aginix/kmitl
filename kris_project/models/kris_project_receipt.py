import logging

from odoo import _, api, fields, models
from odoo.tools import formatLang

_logger = logging.getLogger(__name__)


class KrisProjectReceipt(models.Model):
    _name = "kris.project.receipt"
    _description = "KRIS Project Receipt"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="Installment Number",
        domain="[('project_id', '=', project_id)]",
        ondelete="set null",
    )
    name = fields.Char(
        string="Receipt Number",
        required=True,
        tracking=True,
    )
    date = fields.Date(
        string="Receipt Date",
        required=True,
        tracking=True,
    )
    equipment_cost_in_installment = fields.Monetary(
        string="Equipment Cost in Installment",
        default=0.0,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        tracking=True,
    )
    extra_income = fields.Monetary(
        string="Extra Value",
        default=0.0,
        tracking=True,
    )
    net_amount = fields.Monetary(
        string="Net Amount",
        compute="_compute_net_amount",
        store=True,
    )
    allocation_ids = fields.One2many(
        comodel_name="kris.project.receipt.allocation",
        inverse_name="receipt_id",
        string="Allocation",
    )
    note = fields.Text(
        string="Note",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="project_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )
    project_state = fields.Selection(
        related="project_id.state",
        string="Project State",
    )

    _TRACKED_FIELDS = {
        "name", "date", "amount", "equipment_cost_in_installment", "extra_income",
    }

    def _format_amount(self, amount):
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    def _format_field_value(self, field_name, value):
        if field_name in ("amount", "equipment_cost_in_installment", "extra_income"):
            return self._format_amount(value or 0.0)
        if field_name == "date":
            return str(value) if value else ""
        return str(value) if value else ""

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("skip_message_post"):
            for rec in records:
                if rec.project_id:
                    body = _("บันทึกรายรับ: %s จำนวน %s") % (
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
                body = _("แก้ไขรายรับ %s") % rec.name
                body += "<ul>%s</ul>" % "".join(
                    "<li>%s</li>" % c for c in changes
                )
                rec.project_id.message_post(
                    body=body, subtype_xmlid="mail.mt_note"
                )
        return result

    def action_delete(self):
        self.ensure_one()
        self.unlink()
        return False

    def unlink(self):
        messages = []
        if not self.env.context.get("skip_message_post"):
            for rec in self:
                if rec.project_id:
                    messages.append(
                        (rec.project_id, _("ลบรายรับ: %s") % rec.name)
                    )
        allocation_lines = self.allocation_ids.mapped("allocation_line_id")
        result = super().unlink()
        if allocation_lines:
            allocation_lines._compute_actual_amount()
        for project, body in messages:
            project.message_post(body=body, subtype_xmlid="mail.mt_note")
        return result

    @api.depends("amount", "equipment_cost_in_installment")
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.amount - rec.equipment_cost_in_installment
