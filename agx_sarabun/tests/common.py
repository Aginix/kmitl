# -*- coding: utf-8 -*-
"""Shared fixtures for agx_sarabun tests (P7).

Provides ``SarabunCommon`` — a ``TransactionCase`` base that:

* registers a ``TransientModel`` origin (``test.sarabun.origin``) inheriting the
  adapter mixin, with **callback spies** for the P6 adapter / rollback tests
  (CLAUDE.md abstract-model testing pattern);
* seeds a department, the ``from_record`` document type (the seed xmlid), a
  register sequence (so ``action_send`` can allocate a number — P3 blocks send
  otherwise), administrative positions with holders, and two sarabun users;
* offers helpers to build a document, add routing steps, send and act; and
* a ``mute_pdf`` context manager that stubs the QWeb-PDF freeze on completion
  (``_render_official_pdf`` needs wkhtmltopdf — tests muting it are env-robust).

Every test class should inherit ``SarabunCommon`` and use these helpers so the
setup stays consistent across files.
"""
from contextlib import contextmanager
from unittest.mock import patch

from odoo import fields, models
from odoo.tests.common import TransactionCase, new_test_user


class SarabunOriginSpy(models.TransientModel):
    """Test origin inheriting the adapter mixin, recording callback invocations.

    Used by the P6 adapter tests: drives a real หนังสือ from an origin and
    asserts the lifecycle callbacks fire with the right args (a
    ``sarabun.routing.step``), in the actor's transaction, with no swallow.
    """

    _name = "test.sarabun.origin"
    _description = "Test Sarabun Origin"
    _inherit = "sarabun.document.mixin"

    name = fields.Char()
    # so action_create_sarabun_document resolves the issuing unit in tests
    # (the test user has no employee/department of its own)
    test_department_id = fields.Many2one("hr.department")

    def _get_sarabun_sender_department(self):
        return self.test_department_id or super()._get_sarabun_sender_department()

    # --- callback spies ---
    circulating_count = fields.Integer(default=0)
    completed_count = fields.Integer(default=0)
    returned_count = fields.Integer(default=0)
    rejected_count = fields.Integer(default=0)
    cancelled_count = fields.Integer(default=0)
    step_count = fields.Integer(default=0)
    last_disposition = fields.Char()
    last_reject_note = fields.Char()
    last_step_is_step = fields.Boolean(default=False)

    # flip to make the completed callback raise (rollback test)
    raise_on_completed = fields.Boolean(default=False)

    def _on_sarabun_circulating(self, document):
        self.circulating_count += 1

    def _on_sarabun_completed(self, document):
        if self.raise_on_completed:
            from odoo.exceptions import UserError

            raise UserError("origin refused completion")
        self.completed_count += 1

    def _on_sarabun_returned(self, document, step):
        self.returned_count += 1

    def _on_sarabun_rejected(self, document, step):
        self.rejected_count += 1
        self.last_reject_note = step.note if step else False

    def _on_sarabun_cancelled(self, document):
        self.cancelled_count += 1

    def _on_sarabun_step(self, step, disposition):
        self.step_count += 1
        self.last_disposition = disposition
        # confirm we get a routing.step, not the old recipient object
        self.last_step_is_step = step._name == "sarabun.routing.step"


class SarabunCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Register the TransientModel origin (CLAUDE.md pattern).
        SarabunOriginSpy._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr, ["test.sarabun.origin"], {"module": "agx_sarabun"}
        )

        cls.Doc = cls.env["sarabun.document"]
        cls.Step = cls.env["sarabun.routing.step"]
        cls.Position = cls.env["sarabun.position"]
        cls.Sequence = cls.env["sarabun.document.sequence"]
        cls.Template = cls.env["sarabun.route.template"]
        cls.Origin = cls.env["test.sarabun.origin"]

        # Document type — the seeded from_record type (kind=from_record, auto numbering).
        cls.doc_type = cls.env.ref("agx_sarabun.document_type_from_record")

        # Issuing unit + its register (so action_send can allocate).
        cls.dept = cls.env["hr.department"].create({"name": "กองทดสอบ"})
        cls.sequence = cls.Sequence.create(
            {
                "name": "ทะเบียนหนังสือ กองทดสอบ",
                "code": "REG-TEST",
                "sender_department_id": cls.dept.id,
                "document_type_id": cls.doc_type.id,
            }
        )

        # Two sarabun users.
        cls.user_a = new_test_user(
            cls.env, login="sb_user_a", name="ผู้ใช้ ก",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        cls.user_b = new_test_user(
            cls.env, login="sb_user_b", name="ผู้ใช้ ข",
            groups="base.group_user,agx_sarabun.group_sarabun_user",
        )
        cls.manager = new_test_user(
            cls.env, login="sb_manager", name="ผู้จัดการ",
            groups="base.group_user,agx_sarabun.group_sarabun_manager",
        )

        # Positions: single-holder and multi-holder.
        cls.pos = cls.Position.create(
            {"name": "คณบดีทดสอบ", "code": "DEAN-T", "holder_ids": [(6, 0, cls.user_a.ids)]}
        )
        cls.pos_multi = cls.Position.create(
            {
                "name": "คณะกรรมการทดสอบ",
                "code": "COMM-T",
                "holder_ids": [(6, 0, (cls.user_a + cls.user_b).ids)],
            }
        )

        # Central officers for unit-mode targeting.
        cls.dept.sarabun_officer_ids = [(6, 0, cls.user_a.ids)]

    # ------------------------------------------------------------------ helpers
    def _make_doc(self, subject="หนังสือทดสอบ", sender=None, origin=None, doc_type=None, **vals):
        """Create a draft sarabun.document (standalone unless ``origin`` given)."""
        v = {
            "subject": subject,
            "type_id": (doc_type or self.doc_type).id,
            "sender_department_id": self.dept.id,
        }
        if sender is not None:
            v["sender_user_id"] = sender.id
        if origin is not None:
            v["origin_model"] = origin._name
            v["origin_res_id"] = origin.id
        v.update(vals)
        return self.Doc.create(v)

    def _add_step(self, doc, order=10, verb="sign_approve", target_mode="person",
                  user=None, position=None, department=None, for_info=False):
        """Create a waiting routing step on ``doc``. Defaults: a person-target
        sign_approve step on ``user_a``."""
        v = {
            "document_id": doc.id,
            "order": order,
            "verb": verb,
            "target_mode": target_mode,
            "for_info": for_info,
            "state": "waiting",
        }
        if target_mode == "person":
            v["user_id"] = (user or self.user_a).id
        elif target_mode == "position":
            v["position_id"] = (position or self.pos).id
        elif target_mode == "unit":
            v["department_id"] = (department or self.dept).id
        return self.Step.create(v)

    def _act(self, step, disposition, actor, **vals):
        """Invoke the single act-on-step entry point as ``actor``."""
        return step.act_on_step(disposition, vals or None, actor=actor)

    def _active_step(self, doc):
        """The currently active step of a document (first match)."""
        return doc.routing_step_ids.filtered(lambda s: s.state == "active")[:1]

    @contextmanager
    def mute_pdf(self):
        """Stub the official-PDF render so completion doesn't need wkhtmltopdf."""
        with patch.object(
            type(self.env["sarabun.document"]),
            "_render_official_pdf",
            return_value=b"%PDF-1.4 test",
        ):
            yield
