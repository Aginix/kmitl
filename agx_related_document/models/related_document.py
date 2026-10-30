from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import html2plaintext
from odoo.tools.sql import escape_psql


class RelatedDocument(models.Model):
    """A document cited on a record, as supporting evidence only (ADR-0001).

    Whoever may read the citing record reads its rows: access is derived from
    it, like ``mail.activity``. Who may *change* them is the citing record's
    ``_related_document_check_change`` hook."""

    _name = "related.document"
    _description = "Related Document"
    _order = "sequence, id"

    # The citing document.
    res_model = fields.Char(string="Citing Model", required=True, index=True)
    res_id = fields.Many2oneReference(
        string="Citing ID", model_field="res_model", required=True, index=True
    )
    sequence = fields.Integer(default=10)
    # Empty = an out-of-system document, given by number/subject.
    kind_id = fields.Many2one(
        comodel_name="related.document.kind",
        string="ชนิดเอกสาร",
        ondelete="restrict",
        help="ว่างไว้ = เอกสารนอกระบบ",
    )
    document_number = fields.Char(string="เลขที่")
    document_date = fields.Date(
        string="ลงวันที่",
        help="ใช้แยกเอกสารในระบบที่เลขซ้ำกันข้ามปีงบประมาณ",
    )
    name = fields.Char(string="เรื่อง")
    # The cited in-system document. The row keeps the snapshot above (number,
    # date, subject) so it still reads when the target is gone or unreadable.
    target_res_model = fields.Char(
        compute="_compute_target_res_model", store=True, readonly=False
    )
    target_res_id = fields.Many2oneReference(
        string="เอกสาร", model_field="target_res_model", index=True
    )
    picker_domain = fields.Char(compute="_compute_picker_domain")
    file = fields.Binary(string="ไฟล์แนบ", attachment=True)
    file_name = fields.Char(string="ชื่อไฟล์")
    added_by_id = fields.Many2one(
        comodel_name="res.users",
        string="เพิ่มโดย",
        default=lambda self: self.env.user,
        readonly=True,
    )
    citing_model_label = fields.Char(compute="_compute_citing")
    citing_name = fields.Char(compute="_compute_citing")

    @api.depends("kind_id")
    def _compute_target_res_model(self):
        for rec in self:
            rec.target_res_model = rec.kind_id.sudo().model_name or False

    @api.depends("kind_id")
    def _compute_picker_domain(self):
        for rec in self:
            rec.picker_domain = rec.kind_id.sudo().target_domain or "[]"

    @api.depends("res_model", "res_id")
    def _compute_citing(self):
        for rec in self:
            model = self.env.get(rec.res_model)
            rec.citing_model_label = model._description if model is not None else ""
            rec.citing_name = (
                model.browse(rec.res_id).display_name if model is not None else ""
            )

    # ------------------------------------------------------------------ #
    # Finding the cited document                                           #
    # ------------------------------------------------------------------ #

    def _check_kind_scope(self):
        """Refuse a kind whose ใช้ได้กับ leaves out the citing model."""
        self.ensure_one()
        names = self.kind_id.sudo().citing_model_names
        if names and ",%s," % self.res_model not in names:
            raise ValidationError(
                _("ชนิดเอกสาร %(kind)s ใช้กับเอกสารนี้ไม่ได้", kind=self.kind_id.name)
            )

    def _search_target(self, kind, domain):
        """Search as the user; fall back to sudo only when the kind allows
        looking a typed number up across the user's rights."""
        Document = self.env[kind.model_name]
        try:
            found = Document.search(domain, limit=2)
        except AccessError:
            found = Document.browse()
        if not found and kind.allow_number_lookup:
            found = Document.sudo().search(domain, limit=2)
        return found

    def _find_document(self):
        """The in-system document the row's number names. Raises when the
        number matches none, or several the date does not tell apart."""
        self.ensure_one()
        # sudo: the kind's field settings are ir.model.fields, which regular
        # users cannot read.
        kind = self.kind_id.sudo()
        self._check_kind_scope()
        number = (self.document_number or "").strip()
        if not number or number == "/":
            raise ValidationError(_("กรุณาระบุเลขที่เอกสาร"))
        domain = [(kind._get_number_field(), "=ilike", escape_psql(number))]
        if kind.date_field_id and self.document_date:
            domain.append((kind.date_field_id.name, "=", self.document_date))
        found = self._search_target(kind, domain + kind._get_target_domain())
        if not found:
            raise ValidationError(_("ไม่พบเอกสารเลขที่ %(number)s", number=number))
        if len(found) > 1:
            raise ValidationError(
                _(
                    "พบเอกสารเลขที่ %(number)s มากกว่า 1 ฉบับ กรุณาระบุลงวันที่",
                    number=number,
                )
            )
        return found.sudo()

    def _check_picked_document(self):
        """The document picked from the dropdown, which the client chose and
        so must be re-validated: the user reads it (or the kind allows number
        lookup) and it passes the kind's target domain."""
        self.ensure_one()
        kind = self.kind_id.sudo()
        self._check_kind_scope()
        if self.target_res_model != kind.model_name:
            raise ValidationError(_("เอกสารที่เลือกไม่ตรงกับชนิดเอกสาร"))
        document = self.env[kind.model_name].browse(self.target_res_id)
        if not document.sudo().exists():
            raise ValidationError(_("ไม่พบเอกสารที่เลือก"))
        try:
            document.check_access_rights("read")
            document.check_access_rule("read")
        except AccessError:
            if not kind.allow_number_lookup:
                raise ValidationError(_("ไม่มีสิทธิ์อ้างเอกสารนี้")) from None
        document = document.sudo()
        if not document.filtered_domain(kind._get_target_domain()):
            raise ValidationError(_("เอกสารนี้ไม่อยู่ในเงื่อนไขที่อ้างได้"))
        return document

    def _get_document_subject(self, document):
        """The kind's subject field (plain text, first line), else the
        document's display name."""
        field = self.kind_id.sudo().subject_field_id
        subject = document[field.name] if field else document.display_name
        if field and field.ttype == "html":
            subject = html2plaintext(subject or "")
        subject = (subject or "").strip().split("\n")[0]
        return subject[:120].rstrip() + "…" if len(subject) > 120 else subject

    def _get_snapshot(self, document):
        """The row values that describe ``document``."""
        kind = self.kind_id.sudo()
        vals = {
            "target_res_model": document._name,
            "target_res_id": document.id,
            # The document's own spelling of the number, not the typed one.
            "document_number": document[kind._get_number_field()],
            "name": self._get_document_subject(document),
        }
        if kind.date_field_id:
            vals["document_date"] = document[kind.date_field_id.name]
        return vals

    def _resolve_document(self, written=()):
        """Point each row at the document it cites and snapshot it. Written
        under sudo: it is the system filling in, not the user editing.
        ``written`` names the fields the caller itself wrote, which are kept."""
        for rec in self:
            if not rec.kind_id:
                if rec.target_res_id:
                    rec.sudo().write({"target_res_id": False})
                continue
            if rec.target_res_id:
                document = rec._check_picked_document()
            else:
                document = rec._find_document()
            vals = rec._get_snapshot(document)
            if "name" in written or (rec.name and not rec.target_res_id):
                vals.pop("name")
            vals = {k: v for k, v in vals.items() if rec[k] != v}
            if vals:
                rec.sudo().write(vals)

    @api.onchange("target_res_id")
    def _onchange_target_res_id(self):
        if not (self.kind_id and self.target_res_id):
            return
        try:
            document = self._check_picked_document()
        except ValidationError as e:
            self.target_res_id = False
            return {"warning": {"title": _("เลือกเอกสารไม่ได้"), "message": e.args[0]}}
        snapshot = self._get_snapshot(document)
        self.document_number = snapshot["document_number"]
        self.name = snapshot["name"]
        if "document_date" in snapshot:
            self.document_date = snapshot["document_date"]

    @api.onchange("kind_id", "document_number", "document_date")
    def _onchange_document_number(self):
        if not self.kind_id or not self.document_number:
            return
        try:
            document = self._find_document()
        except ValidationError as e:
            self.target_res_id = False
            return {"warning": {"title": _("ไม่พบเอกสาร"), "message": e.args[0]}}
        self.target_res_id = document.id
        self.name = self._get_document_subject(document)

    @api.constrains("document_number", "name")
    def _check_identified(self):
        for rec in self:
            if not (rec.document_number or rec.name or rec.target_res_id):
                raise ValidationError(_("กรุณาระบุเลขที่หรือเรื่องของเอกสารอ้างอิง"))

    # ------------------------------------------------------------------ #
    # Opening the cited / citing document                                  #
    # ------------------------------------------------------------------ #

    def _form_action(self, model, res_id):
        return {
            "type": "ir.actions.act_window",
            "res_model": model,
            "res_id": res_id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "current",
        }

    def action_open_document(self):
        """Open the cited document as the reader, never under sudo."""
        self.ensure_one()
        if not self.target_res_id:
            raise UserError(_("เอกสารนอกระบบ ไม่มีเอกสารให้เปิด"))
        model = self.env.get(self.target_res_model)
        if model is None or not model.browse(self.target_res_id).sudo().exists():
            raise UserError(_("เอกสารถูกลบแล้ว"))
        document = model.browse(self.target_res_id)
        try:
            document.check_access_rights("read")
            document.check_access_rule("read")
        except AccessError:
            raise UserError(_("ไม่มีสิทธิ์เปิดเอกสารนี้")) from None
        return self._form_action(self.target_res_model, self.target_res_id)

    def action_open_citing(self):
        self.ensure_one()
        return self._form_action(self.res_model, self.res_id)

    @api.model
    def _action_cited_by(self, targets):
        """List the rows citing ``targets``, only those whose citing document
        the user can read."""
        rows = self.sudo().search(
            [
                ("target_res_model", "=", targets._name),
                ("target_res_id", "in", targets.ids),
            ]
        )
        rows = rows.with_env(self.env)._filter_access_rules("read")
        return {
            "type": "ir.actions.act_window",
            "name": _("ถูกอ้างอิงโดย"),
            "res_model": self._name,
            "view_mode": "tree",
            "views": [
                (
                    self.env.ref(
                        "agx_related_document.view_related_document_cited_by_tree"
                    ).id,
                    "tree",
                )
            ],
            "domain": [("id", "in", rows.ids)],
            "target": "current",
        }

    # ------------------------------------------------------------------ #
    # Access follows the citing document                                   #
    # ------------------------------------------------------------------ #

    def _readable_citing(self, rows_sudo, method):
        """Rows of ``rows_sudo`` whose citing document passes ``method``
        ('_filter_access_rules' or its python twin) for read."""
        by_model = defaultdict(set)
        for row in rows_sudo:
            by_model[row.res_model].add(row.res_id)
        valid = set()
        for model, ids in by_model.items():
            if model not in self.env:
                continue
            Citing = self.env[model]
            if not Citing.check_access_rights("read", raise_exception=False):
                continue
            readable = getattr(Citing.browse(ids), method)("read")
            valid.update((model, rid) for rid in readable.ids)
        return rows_sudo.filtered(lambda r: (r.res_model, r.res_id) in valid)

    def _filter_access_rules(self, operation):
        return self._readable_citing(self.sudo(), "_filter_access_rules").sudo(
            self.env.su
        )

    def _filter_access_rules_python(self, operation):
        return self._readable_citing(self.sudo(), "_filter_access_rules_python").sudo(
            self.env.su
        )

    def read(self, fields=None, load="_classic_read"):
        # A plain read only applies ir.rules, so check the citing document too.
        self.check_access_rule("read")
        return super().read(fields, load=load)

    @api.model
    def _search(
        self,
        args,
        offset=0,
        limit=None,
        order=None,
        count=False,
        access_rights_uid=None,
    ):
        if self.env.is_superuser():
            return super()._search(
                args,
                offset=offset,
                limit=limit,
                order=order,
                count=count,
                access_rights_uid=access_rights_uid,
            )
        ids = list(
            super()._search(
                args,
                offset=offset,
                limit=limit,
                order=order,
                count=False,
                access_rights_uid=access_rights_uid,
            )
        )
        user = self.with_user(access_rights_uid or self._uid)
        allowed = set(user.browse(ids)._filter_access_rules("read").ids)
        if count:
            return len(allowed)
        return [rid for rid in ids if rid in allowed]

    # ------------------------------------------------------------------ #
    # Who may change the rows: the citing record's hook                    #
    # ------------------------------------------------------------------ #

    def _citing_groups(self):
        groups = defaultdict(lambda: self.browse())
        for rec in self:
            groups[(rec.res_model, rec.res_id)] |= rec
        return groups

    def _check_change(self, operation):
        """Ask each citing record whether the user may change its rows."""
        if self.env.su:
            return
        for (model, res_id), rows in self._citing_groups().items():
            if model not in self.env or not hasattr(
                self.env[model], "_related_document_check_change"
            ):
                raise ValidationError(
                    _("เอกสารนี้ไม่รองรับเอกสารอ้างอิง (%(model)s)", model=model)
                )
            self.env[model].browse(res_id)._related_document_check_change(
                rows, operation
            )

    def _log(self, body):
        """Note on the citing record's chatter, under sudo: a reader may
        lack posting rights."""
        for (model, res_id), rows in self._citing_groups().items():
            citing = self.env[model].sudo().browse(res_id).exists()
            if not citing or not hasattr(citing, "message_post"):
                continue
            citing.message_post(
                body=body
                % {
                    "documents": ", ".join(
                        filter(None, (r.document_number or r.name for r in rows))
                    ),
                    "user": self.env.user.name,
                },
                subtype_xmlid="mail.mt_note",
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_change("create")
        records._resolve_document()
        records._log(_("เพิ่มเอกสารอ้างอิง %(documents)s โดย %(user)s"))
        return records

    def write(self, vals):
        if not self.env.su:
            if {"res_model", "res_id"} & set(vals):
                raise UserError(_("ย้ายเอกสารอ้างอิงไปเอกสารอื่นไม่ได้"))
            self._check_change("write")
        lookup = {"kind_id", "document_number", "document_date"} & set(vals)
        if lookup and "target_res_id" not in vals:
            # Retyped number: find the document again.
            vals = dict(vals, target_res_id=False)
        res = super().write(vals)
        if lookup or "target_res_id" in vals:
            self._resolve_document(written=set(vals))
        return res

    def unlink(self):
        self._check_change("unlink")
        if not self.env.context.get("related_document_cascade"):
            self._log(_("ลบเอกสารอ้างอิง %(documents)s โดย %(user)s"))
        return super().unlink()
