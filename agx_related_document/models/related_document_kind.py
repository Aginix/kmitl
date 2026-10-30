from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

CITED_BY_ACTION_NAME = "ถูกอ้างอิงโดย"
CITED_BY_ACTION_CODE = 'action = env["related.document"]._action_cited_by(records)'


class RelatedDocumentKind(models.Model):
    """An in-system document kind a record may cite, configured by the
    administrators instead of a bridge module per kind (ADR-0001).

    With ``allow_number_lookup`` a typed number is also looked up under sudo,
    so anyone can learn the subject of a record whose number they type: only
    enable it for models whose subjects may be shown that way."""

    _name = "related.document.kind"
    _description = "Related Document Kind"
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
    citing_model_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="related_document_kind_citing_model_rel",
        column1="kind_id",
        column2="model_id",
        string="ใช้ได้กับ",
        domain=[("transient", "=", False)],
        help="เอกสารที่อ้างได้ ว่างไว้ = ทุกเอกสารที่เปิดใช้เอกสารอ้างอิง",
    )
    # ",a,b," — lets the row's kind dropdown filter without reading ir.model,
    # which regular users cannot.
    citing_model_names = fields.Char(compute="_compute_citing_model_names", store=True)
    target_domain = fields.Char(
        string="เงื่อนไขเอกสารที่อ้างได้",
        default="[]",
        help="เช่น เฉพาะที่อนุมัติแล้ว ใช้กับทั้งรายการที่เลือกและการพิมพ์เลขที่",
    )
    allow_number_lookup = fields.Boolean(
        string="พิมพ์เลขที่ค้นข้ามสิทธิ์",
        help="พิมพ์เลขที่ให้ตรงทุกตัวอักษรเพื่ออ้างเอกสารที่ผู้ใช้ไม่มีสิทธิ์อ่าน ผู้ใช้จะเห็น เรื่อง ของเอกสารนั้น",
    )
    show_cited_by = fields.Boolean(
        string="แสดง ถูกอ้างอิงโดย",
        help="เพิ่มเมนู ถูกอ้างอิงโดย ใน Action ของเอกสารชนิดนี้",
    )

    @api.depends("citing_model_ids")
    def _compute_citing_model_names(self):
        for rec in self:
            names = rec.citing_model_ids.mapped("model")
            rec.citing_model_names = ",%s," % ",".join(names) if names else False

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

    def _get_target_domain(self):
        self.ensure_one()
        return safe_eval(self.target_domain or "[]", {"uid": self.env.uid})

    # ------------------------------------------------------------------ #
    # ถูกอ้างอิงโดย — an action-menu entry on the target model              #
    # ------------------------------------------------------------------ #

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["related.document.kind"]._sync_cited_by_actions()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._sync_cited_by_actions()
        return res

    def unlink(self):
        res = super().unlink()
        self._sync_cited_by_actions()
        return res

    @api.model
    def _sync_cited_by_actions(self):
        """Keep one bound server action per model that has an active kind
        with ``show_cited_by``, and none elsewhere. Done under sudo: the
        action is plumbing, admins only edit the kind."""
        Action = self.env["ir.actions.server"].sudo()
        wanted = self.sudo().search([("show_cited_by", "=", True)]).model_id
        existing = Action.search([("code", "=", CITED_BY_ACTION_CODE)])
        stale = existing.filtered(lambda a: a.binding_model_id not in wanted)
        bound = (existing - stale).binding_model_id
        stale.unlink()
        for model in wanted - bound:
            Action.create(
                {
                    "name": CITED_BY_ACTION_NAME,
                    "model_id": model.id,
                    "binding_model_id": model.id,
                    "state": "code",
                    "code": CITED_BY_ACTION_CODE,
                }
            )
