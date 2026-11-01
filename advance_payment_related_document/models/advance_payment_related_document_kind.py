from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AdvancePaymentRelatedDocumentKind(models.Model):
    """An in-system document kind a loan may cite, configured by the
    administrators instead of a bridge module per kind (ADR-0029).

    Rows of a kind are looked up by number under sudo, so anyone can learn
    the subject of a record whose number they type: only configure models
    whose subjects may be shown that way."""

    _name = "advance.payment.related.document.kind"
    _description = "Advance Payment Related Document Kind"
    _order = "sequence, name"

    name = fields.Char(string="ชนิดเอกสาร", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
        domain=[("transient", "=", False)],
    )
    model_name = fields.Char(related="model_id.model", store=True, readonly=True)
    number_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="ช่องเลขที่",
        ondelete="cascade",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'char'), ('store', '=', True)]",
        help="ว่างไว้ = ใช้ชื่อหลักของเอกสาร (_rec_name)",
    )
    subject_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="ช่องเรื่อง",
        ondelete="set null",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ('char', 'text', 'html'))]",
        help="ว่างไว้ = ใช้ชื่อที่แสดงของเอกสาร",
    )
    date_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="ช่องลงวันที่",
        ondelete="set null",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'date'), ('store', '=', True)]",
        help="ใช้แยกเอกสารที่เลขซ้ำกัน เช่น เลขที่เริ่มนับใหม่ทุกปีงบประมาณ",
    )

    @api.constrains("model_id", "number_field_id", "subject_field_id", "date_field_id")
    def _check_fields_on_model(self):
        for rec in self:
            for field in (rec.number_field_id, rec.subject_field_id, rec.date_field_id):
                if field and field.model_id != rec.model_id:
                    raise ValidationError(
                        _(
                            "%(field)s is not a field of %(model)s.",
                            field=field.field_description,
                            model=rec.model_id.name,
                        )
                    )

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.number_field_id = self.subject_field_id = self.date_field_id = False

    def _get_number_field(self):
        self.ensure_one()
        return self.number_field_id.name or self.env[self.model_name]._rec_name
