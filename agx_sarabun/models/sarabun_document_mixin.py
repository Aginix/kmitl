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

    sarabun_document_ids = fields.One2many(
        comodel_name="sarabun.document",
        compute="_compute_sarabun_documents",
        string="Sarabun Documents",
    )
    sarabun_document_count = fields.Integer(
        compute="_compute_sarabun_documents",
        string="Sarabun Document Count",
    )

    def _compute_sarabun_documents(self):
        SarabunDocument = self.env["sarabun.document"]
        for record in self:
            documents = SarabunDocument.search(
                [
                    ("origin_model", "=", record._name),
                    ("origin_res_id", "=", record.id),
                ]
            )
            record.sarabun_document_ids = documents
            record.sarabun_document_count = len(documents)

    def _prepare_sarabun_document_vals(self):
        """
        Prepare values for creating a sarabun document.
        Override this method in inheriting models.

        Returns:
            dict: Values for sarabun.document create()
        """
        self.ensure_one()
        # NOTE (P1): adapter hardening (1:N, active_sarabun_document_id, new
        # lifecycle callbacks passing a sarabun.routing.step, atomic rollback) is
        # P6 — see ADR-0004. Here we only keep the contract loadable for the 5
        # consumer modules and align the type field name (document_type_id → type_id).
        doc_type = self.env.ref(
            "agx_sarabun.document_type_from_record", raise_if_not_found=False
        )
        return {
            "type_id": doc_type.id if doc_type else False,
            "subject": self._get_sarabun_subject(),
            "origin_model": self._name,
            "origin_res_id": self.id,
        }

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

    def _on_sarabun_completed(self, document):
        """
        Callback when sarabun document routing is completed.
        Override this to update your record state.

        Args:
            document: The completed sarabun.document record
        """
        pass

    def _on_sarabun_rejected(self, document, recipient):
        """
        Callback when sarabun document is rejected.
        Override this to handle rejection.

        Args:
            document: The sarabun.document record
            recipient: The sarabun.document.recipient record that rejected
        """
        pass

    def _on_sarabun_action(self, document, recipient, action):
        """
        Callback for every action on sarabun document.
        Called for acknowledge, approve, and reject actions.
        Override this to track all actions on the document.

        Args:
            document: The sarabun.document record
            recipient: The sarabun.document.recipient record that performed the action
            action: The action type ('acknowledge', 'approve', 'reject')

        Example:
            def _on_sarabun_action(self, document, recipient, action):
                self.message_post(
                    body=f"Sarabun action: {action} by {recipient.actioned_by.name}"
                )
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
