from odoo import fields, models


class RelatedDocumentOne2many(fields.One2many):
    """The One2many of the mixin. It names the model of its rows by itself —
    the inverse ``res_id`` carries no model — so a row added through the
    field belongs to the right citing model on every model using it."""

    def _setup_attrs(self, model_class, name):
        super()._setup_attrs(model_class, name)
        self.domain = [("res_model", "=", model_class._name)]
        self.context = {"default_res_model": model_class._name}


class RelatedDocumentMixin(models.AbstractModel):
    """Lets a model cite Related documents (ADR-0001), like
    ``mail.activity.mixin`` lets it take activities. Additions and removals
    are logged in the chatter when the model has one."""

    _name = "related.document.mixin"
    _description = "Related Document Mixin"

    related_document_ids = RelatedDocumentOne2many(
        comodel_name="related.document",
        inverse_name="res_id",
        string="เอกสารอ้างอิง",
        copy=False,
    )
    related_document_count = fields.Integer(compute="_compute_related_document_count")

    def _compute_related_document_count(self):
        for record in self:
            record.related_document_count = len(record.related_document_ids)

    def _related_document_check_change(self, rows, operation):
        """Raise unless the user may ``operation`` ('create', 'write' or
        'unlink') these rows of this record. By default: whoever may write
        the record. A module narrows or widens it, e.g. by the record's state."""
        self.ensure_one()
        self.check_access_rights("write")
        self.check_access_rule("write")

    def unlink(self):
        rows = (
            self.env["related.document"]
            .sudo()
            .search([("res_model", "=", self._name), ("res_id", "in", self.ids)])
        )
        res = super().unlink()
        rows.with_context(related_document_cascade=True).unlink()
        return res
