from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext
from odoo.tools.sql import escape_psql

CLOSED_STATES = ("done", "cancel")


class AdvancePaymentRelatedDocument(models.Model):
    """A further document cited on a loan beside its source — evidence only
    (advance_payment ADR-0029)."""

    _name = "advance.payment.related.document"
    _description = "Advance Payment Related Document"
    _order = "sequence, id"

    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="สัญญายืมเงิน",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    # Empty = an out-of-system document, given by number/subject. A kind is
    # an in-system model the administrators configured (ADR-0029).
    kind_id = fields.Many2one(
        comodel_name="advance.payment.related.document.kind",
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
    # The in-system document, set from the typed number. Kept off the views:
    # a reference widget name_get()s the document, which the reader may not
    # be allowed to read (advance_payment ADR-0023).
    res_model = fields.Char(string="Document Model", readonly=True)
    res_id = fields.Many2oneReference(
        string="Document ID", model_field="res_model", readonly=True
    )
    file = fields.Binary(string="ไฟล์แนบ", attachment=True)
    file_name = fields.Char(string="ชื่อไฟล์")
    added_by_id = fields.Many2one(
        comodel_name="res.users",
        string="เพิ่มโดย",
        default=lambda self: self.env.user,
        readonly=True,
    )

    def _get_document_subject(self, document):
        """The kind's subject field (plain text, first line), else the
        document's display name. Read under sudo — so is the kind: regular
        users cannot read ir.model.fields."""
        field = self.kind_id.sudo().subject_field_id
        subject = document[field.name] if field else document.display_name
        if field and field.ttype == "html":
            subject = html2plaintext(subject or "")
        subject = (subject or "").strip().split("\n")[0]
        return subject[:120].rstrip() + "…" if len(subject) > 120 else subject

    def _find_document(self):
        """The in-system document the row's number names, under sudo — the
        reader need not be able to open it. Raises when the number matches
        none, or several the date does not tell apart."""
        self.ensure_one()
        # sudo: the kind's field settings are ir.model.fields, which regular
        # users cannot read.
        kind = self.kind_id.sudo()
        number = (self.document_number or "").strip()
        if not number or number == "/":
            raise ValidationError(_("กรุณาระบุเลขที่เอกสาร"))
        Document = self.env[kind.model_name].sudo()
        domain = [(kind._get_number_field(), "=ilike", escape_psql(number))]
        if kind.date_field_id and self.document_date:
            domain.append((kind.date_field_id.name, "=", self.document_date))
        found = Document.search(domain, limit=2)
        if not found:
            raise ValidationError(_("ไม่พบเอกสารเลขที่ %(number)s", number=number))
        if len(found) > 1:
            raise ValidationError(
                _(
                    "พบเอกสารเลขที่ %(number)s มากกว่า 1 ฉบับ กรุณาระบุลงวันที่",
                    number=number,
                )
            )
        return found

    def _resolve_document(self):
        """Point the row at the document its number names. Written under sudo:
        it is the system filling in, not the user editing — a borrower adding
        a row to an outstanding loan must not trip the draft-only edit rule."""
        for rec in self:
            if not rec.kind_id:
                if rec.res_model or rec.res_id:
                    rec.sudo().write({"res_model": False, "res_id": False})
                continue
            document = rec._find_document()
            vals = {}
            if (rec.res_model, rec.res_id) != (document._name, document.id):
                vals.update(res_model=document._name, res_id=document.id)
            # Store the document's own spelling of the number, not the typed one.
            number = document[rec.kind_id.sudo()._get_number_field()]
            if number and number != rec.document_number:
                vals["document_number"] = number
            if not rec.name:
                vals["name"] = rec._get_document_subject(document)
            if vals:
                rec.sudo().write(vals)

    @api.onchange("kind_id", "document_number", "document_date")
    def _onchange_document_number(self):
        if not self.kind_id or not self.document_number:
            return
        try:
            document = self._find_document()
        except ValidationError as e:
            return {"warning": {"title": _("ไม่พบเอกสาร"), "message": e.args[0]}}
        self.name = self._get_document_subject(document)

    @api.constrains("document_number", "name")
    def _check_identified(self):
        for rec in self:
            if not rec.document_number and not rec.name:
                raise ValidationError(_("กรุณาระบุเลขที่หรือเรื่องของเอกสารอ้างอิง"))

    # ------------------------------------------------------------------ #
    # Who may change the rows, and until when (ADR-0029)                   #
    # ------------------------------------------------------------------ #

    def _is_staff(self):
        """Unit finance (the User tier) and the loan officer, who implies it."""
        return self.env.su or self.env.user.has_group(
            "advance_payment.group_advance_payment_user"
        )

    def _check_loan_open(self):
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        closed = self.mapped("advance_payment_id").filtered(
            lambda loan: loan.state in CLOSED_STATES
        )
        if closed:
            raise UserError(
                _(
                    "สัญญา %(loans)s ปิดหรือยกเลิกแล้ว แก้ไขเอกสารอ้างอิงไม่ได้",
                    loans=", ".join(closed.mapped("name")),
                )
            )

    def _check_borrower_may_change(self):
        """A borrower changes only the rows they added, and only in draft."""
        if self._is_staff():
            return
        for rec in self:
            if rec.added_by_id != self.env.user or rec.advance_payment_id.state != (
                "draft"
            ):
                raise UserError(
                    _("ลบหรือแก้ไขได้เฉพาะเอกสารที่คุณเพิ่มเอง และขณะที่คำขอยังเป็นแบบร่าง")
                )

    def _log(self, body):
        for loan in self.mapped("advance_payment_id"):
            rows = self.filtered(lambda r, loan=loan: r.advance_payment_id == loan)
            # sudo: an endorser may read the loan without posting rights.
            loan.sudo().message_post(
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
        records._check_loan_open()
        records._resolve_document()
        records._log(_("เพิ่มเอกสารอ้างอิง %(documents)s โดย %(user)s"))
        return records

    def write(self, vals):
        if not self.env.su:
            self._check_loan_open()
            self._check_borrower_may_change()
        res = super().write(vals)
        if {"kind_id", "document_number", "document_date"} & set(vals):
            self._resolve_document()
        return res

    def unlink(self):
        self._check_loan_open()
        self._check_borrower_may_change()
        self._log(_("ลบเอกสารอ้างอิง %(documents)s โดย %(user)s"))
        return super().unlink()
