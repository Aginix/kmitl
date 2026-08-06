# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SarabunDocumentMixin(models.AbstractModel):
    """
    Mixin for models that can create Sarabun documents.

    Inherit this mixin and implement _prepare_sarabun_document_vals()
    to enable creating sarabun documents from your model.

    Example:
        class PurchaseRequest(models.Model):
            _inherit = ["purchase.request", "sarabun.document.mixin"]

            def _prepare_sarabun_document_vals(self):
                return {
                    "subject": f"Purchase Request: {self.name}",
                }
    """

    _name = "sarabun.document.mixin"
    _description = "Sarabun Document Mixin"

    # Owned by the mixin (ADR-0004). The relation lives on the Document
    # (origin_model + origin_res_id), so 1:N is free; reject→duplicate yields a
    # second linked Document. This is a *polymorphic* link, so sarabun_document_ids
    # is a computed pseudo-O2m (search-based) — NOT a real ORM One2many; and
    # active_sarabun_document_id is non-stored computed, never a stored compute over
    # a search (§8.4).
    sarabun_document_ids = fields.One2many(
        comodel_name="sarabun.document",
        compute="_compute_sarabun_documents",
        string="หนังสือ (Documents)",
        help="All หนังสือ spawned from this record (1:N).",
    )
    active_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        compute="_compute_sarabun_documents",
        string="หนังสือฉบับปัจจุบัน (Active Document)",
        help="The current live Document (most recent non-terminal one); others are "
        "superseded (rejected → duplicated). Replaces per-consumer main_sarabun_document_id.",
    )
    sarabun_document_count = fields.Integer(
        compute="_compute_sarabun_documents",
        string="Sarabun Document Count",
    )
    sarabun_has_live_document = fields.Boolean(
        compute="_compute_sarabun_documents",
        string="Has Live หนังสือ",
        help="True while a non-terminal Document exists (draft/circulating/"
        "completed/returned). Gate the 'create หนังสือ' button on this — NOT on "
        "sarabun_document_count — so a fresh one can be issued after a terminal "
        "outcome (rejected/cancelled), while a returned doc is revised in place.",
    )
    # Status reflected back onto the origin so users on the source form can see
    # where the หนังสือ is (draft-not-sent, how far the route has progressed).
    sarabun_state = fields.Selection(
        selection=[
            ("draft", "ร่าง (Draft)"),
            ("circulating", "กำลังดำเนินการ (Circulating)"),
            ("completed", "เสร็จสิ้น (Completed)"),
            ("returned", "ตีกลับ (Returned)"),
            ("rejected", "ปฏิเสธ (Rejected)"),
            ("cancelled", "ยกเลิก (Cancelled)"),
        ],
        string="สถานะหนังสือ (Sarabun Status)",
        compute="_compute_sarabun_documents",
        help="State of the current live หนังสือ, mirrored onto the origin record.",
    )
    sarabun_is_draft = fields.Boolean(
        string="หนังสือยังเป็นร่าง (Sarabun Draft)",
        compute="_compute_sarabun_documents",
        help="A หนังสือ was created from this record but not yet sent (still draft).",
    )
    sarabun_state_label = fields.Char(
        string="สถานะการเดินหนังสือ",
        compute="_compute_sarabun_documents",
        help="Human-readable status of the current หนังสือ (state + routing progress).",
    )

    def _compute_sarabun_documents(self):
        SarabunDocument = self.env["sarabun.document"]
        for record in self:
            documents = SarabunDocument.search(
                [
                    ("origin_model", "=", record._name),
                    ("origin_res_id", "=", record.id),
                ],
                order="id desc",
            )
            record.sarabun_document_ids = documents
            record.sarabun_document_count = len(documents)
            live = documents.filtered(lambda d: d.state not in ("rejected", "cancelled"))
            active = live[:1] or documents[:1]
            record.active_sarabun_document_id = active
            record.sarabun_has_live_document = bool(live)
            record.sarabun_state = active.state or False
            record.sarabun_is_draft = active.state == "draft"
            record.sarabun_state_label = active._status_label() if active else False

    def _prepare_sarabun_document_vals(self):
        """Build the ``sarabun.document`` create vals.

        **Owned by the mixin — do not override.** Customise via the hooks instead:
        ``_get_sarabun_subject`` (เรื่อง), ``_get_sarabun_document_type`` (type →
        sequence/route/template) and ``_get_sarabun_sender_department`` (issuing
        ส่วนงาน). This keeps the origin link (origin_model/origin_res_id) and the
        number-assigned-at-send invariant impossible to break by accident.

        Returns:
            dict: Values for sarabun.document create()
        """
        self.ensure_one()
        doc_type = self._get_sarabun_document_type()
        vals = {
            "type_id": doc_type.id if doc_type else False,
            "subject": self._get_sarabun_subject(),
            "origin_model": self._name,
            "origin_res_id": self.id,
        }
        # The official number is NOT assigned at create — only the issuing ส่วนงาน
        # is supplied; ลงทะเบียน happens atomically at completion, when the final
        # approver signs (ADR-0010). Omit when unresolved so the document's own
        # default applies.
        dept = self._get_sarabun_sender_department()
        if dept:
            vals["sender_department_id"] = dept.id
        return vals

    def _get_sarabun_document_type(self):
        """The from_record sarabun.document.type (binds sequence/route/template).
        Override to pick a specific type."""
        return self.env.ref(
            "agx_sarabun.document_type_from_record", raise_if_not_found=False
        )

    def _get_sarabun_sender_department(self):
        """The issuing ส่วนงาน. Defaults to the current user's employee department;
        override per origin record."""
        employee = self.env.user.employee_id
        return employee.department_id if employee else self.env["hr.department"]

    def _get_sarabun_subject(self):
        """
        Get the subject for the sarabun document.
        Override this for custom subject formatting.
        """
        return self.display_name

    def action_create_sarabun_document(self):
        """Create a sarabun document from this record"""
        self.ensure_one()
        vals = self._prepare_sarabun_document_vals()
        document = self.env["sarabun.document"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_submit_to_sarabun(self):
        """Spawn the หนังสือ (draft) from this record and open it.

        The single sanctioned submit entry point for consumers: it creates the
        Document, posts a standard chatter note, and returns the open-form action.
        Override :meth:`_sarabun_submit_guard` to gate submission, and the
        ``_get_sarabun_*`` hooks to customise the Document — a consumer should not
        need to reimplement this method.
        """
        self.ensure_one()
        if not self._sarabun_submit_guard():
            return False
        action = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(action["res_id"])
        self._sarabun_post("submitted", document)
        return action

    def _sarabun_submit_guard(self):
        """Return True to allow :meth:`action_submit_to_sarabun` (default).
        Override to gate, e.g. ``return self.state == "submitted"``."""
        self.ensure_one()
        return True

    def action_view_sarabun_documents(self):
        """View related sarabun documents"""
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Sarabun Documents"),
            "res_model": "sarabun.document",
            "view_mode": "tree,form",
            "domain": [
                ("origin_model", "=", self._name),
                ("origin_res_id", "=", self.id),
            ],
            "context": {
                "default_origin_model": self._name,
                "default_origin_res_id": self.id,
            },
        }

        if self.sarabun_document_count == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.sarabun_document_ids[0].id

        return action

    # === Standard chatter for lifecycle events (centralised, translatable) ===
    def _sarabun_note(self, kind, document, step=None):
        """The chatter body posted for a lifecycle event.

        ``kind`` ∈ submitted / circulating / completed / returned / rejected /
        cancelled. Override to reword, or return a falsy value to suppress the
        note for a kind while still running the origin's state transition.
        ``step`` (when present) carries the acting user and the mandatory reason.
        """
        self.ensure_one()
        reason = (step and step.note) or _("No reason provided")
        actor = (step and step.acted_by_id.name) or _("Unknown")
        return {
            "submitted": _("Submitted to Sarabun for approval: %s") % document.name,
            "circulating": _("Sent for approval via Sarabun: %s") % document.name,
            "completed": _("Approved via Sarabun: %s") % document.name,
            "returned": _(
                "Returned via Sarabun for revision by %(actor)s. Reason: %(reason)s"
            ) % {"actor": actor, "reason": reason},
            "rejected": _(
                "Rejected via Sarabun by %(actor)s. Reason: %(reason)s"
            ) % {"actor": actor, "reason": reason},
            "cancelled": _("Cancelled via Sarabun (ยกเลิกการส่ง): %s") % document.name,
        }.get(kind)

    def _sarabun_post(self, kind, document, step=None):
        """Post the standard :meth:`_sarabun_note` for ``kind`` (skipped if empty)."""
        body = self._sarabun_note(kind, document, step)
        if body:
            self.message_post(body=body, subtype_xmlid="mail.mt_note")

    # === Lifecycle callbacks (ADR-0004 / DESIGN §8.6 contract) ===
    # All run in the actor's transaction; a raising callback rolls the action back
    # (no swallow). The engine fires the matching specific callback below first,
    # then the generic _on_sarabun_step last.
    #
    # Each default body posts the standard chatter note, so an origin override does
    # ONLY its genuine state transition and calls super() to keep the note — or
    # omits the override entirely to get an audit-only note for free.

    def _on_sarabun_circulating(self, document):
        """Called when the Document is sent (draft/returned → circulating)."""
        self._sarabun_post("circulating", document)

    def _on_sarabun_completed(self, document):
        """Called when every gating step is positively completed."""
        self._sarabun_post("completed", document)

    def _on_sarabun_returned(self, document, step):
        """Called when the Document is returned for revision — an approver's ตีกลับ,
        or (via :meth:`_on_sarabun_recalled`) the sender's ดึงกลับ. ``step`` is the
        returning routing step, or an empty recordset for ดึงกลับ."""
        self._sarabun_post("returned", document, step)

    def _on_sarabun_rejected(self, document, step):
        """Called when the Document is rejected (ปฏิเสธ, terminal). ``step`` is the
        rejecting routing step."""
        self._sarabun_post("rejected", document, step)

    def _on_sarabun_cancelled(self, document):
        """Called when the sender withdraws the Document terminally (ยกเลิกการส่ง,
        ADR-0006): the registered number is voided and the Document lands in
        ``cancelled``."""
        self._sarabun_post("cancelled", document)

    def _on_sarabun_recalled(self, document):
        """Called when the sender pulls a circulating Document back to edit
        (ดึงกลับ, ADR-0006): the number is KEPT and the Document lands in
        ``returned``, re-sendable. Fired by the engine's ``action_pull_back``.
        Defaults to the ตีกลับ handler with an empty step so an origin's
        returned-handling applies unchanged; override for distinct behaviour/wording.
        """
        self._on_sarabun_returned(document, step=self.env["sarabun.routing.step"])

    def _on_sarabun_step(self, step, disposition):
        """Generic per-step callback for every disposition (fired last).

        Args:
            step: the ``sarabun.routing.step`` acted on (never the old recipient)
            disposition: 'complete' / 'direct' / 'delegate' / 'return' / 'reject'
        """
        pass

    def _get_sarabun_report_action(self):
        """
        Return ir.actions.report to use for Sarabun document rendering.
        Override this to delegate report rendering to origin model's report.

        When a Sarabun Document is printed/downloaded from portal, it will
        use this report action instead of the default Sarabun report.

        Returns:
            ir.actions.report record or False

        Example:
            def _get_sarabun_report_action(self):
                return self.env.ref("my_module.action_report_my_model")
        """
        return False
