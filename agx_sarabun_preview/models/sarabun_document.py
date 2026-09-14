# -*- coding: utf-8 -*-
"""Routing-timeline preview extension for sarabun.document.

Adds the ``routing_preview_json`` computed field (and its helpers) that the
SarabunRoutingTimeline OWL widget consumes on the document form.  All business
logic lives in ``agx_sarabun``; this module only adds the serialization surface.
"""
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    routing_preview_json = fields.Text(
        compute="_compute_routing_preview_json",
        string="Routing Timeline Payload",
        help="Pre-rendered JSON of the current attempt's Route consumed by the "
        "SarabunRoutingTimeline OWL widget on the form and the send wizard. "
        "Not stored — re-fires on every routing-step change so the timeline "
        "reflects the live chain.",
    )

    @api.depends(
        "attempt_seq",
        "routing_step_ids.order",
        "routing_step_ids.state",
        "routing_step_ids.disposition",
        "routing_step_ids.verb",
        "routing_step_ids.for_info",
        "routing_step_ids.is_originator",
        "routing_step_ids.target_mode",
        "routing_step_ids.target_name",
        "routing_step_ids.acted_by_id",
        "routing_step_ids.acted_date",
        "routing_step_ids.activated_date",
        "routing_step_ids.note",
        "routing_step_ids.delegated_to_id",
        "routing_step_ids.preview_holder_ids",
        "routing_step_ids.actor_user_ids",
    )
    def _compute_routing_preview_json(self):
        """Serialize the live Route for the SarabunRoutingTimeline OWL widget.
        Both the form and the send wizard read this — the wizard's field is a
        ``related`` mirror so one payload feeds both surfaces uniformly."""
        for record in self:
            record.routing_preview_json = json.dumps(
                record._build_routing_preview_payload(record.routing_step_ids),
                ensure_ascii=False,
            )

    _PREVIEW_NOTE_MAX = 120

    def _build_routing_step_payload(self, step):
        """One step-card dict consumed by the timeline widget. Placed on the
        document so a single entry point owns date formatting, note truncation,
        and the escape contract for user text (delivered via OWL ``t-esc``)."""
        self.ensure_one()
        if step.state == "waiting":
            # No snapshot yet — show who WOULD hold the step if it activated now.
            holders = step.preview_holder_ids
        else:
            holders = step.actor_user_ids.mapped("employee_id") or step.preview_holder_ids
        note_full = (step.note or "").strip()
        note_short = None
        if note_full:
            note_short = (
                note_full[: self._PREVIEW_NOTE_MAX] + "…"
                if len(note_full) > self._PREVIEW_NOTE_MAX
                else note_full
            )
        return {
            "id": step.id,
            "order": step.order,
            "verb_name": step.verb.name or "",
            "target_mode": step.target_mode,
            "target_name": step.target_name or "",
            "holders": [{"id": h.id, "name": h.name} for h in holders],
            "state": step.state,
            "disposition": step.disposition or None,
            "is_originator": step.is_originator,
            "for_info": step.for_info,
            "delegated_to": (
                {"id": step.delegated_to_id.id, "name": step.delegated_to_id.name}
                if step.delegated_to_id
                else None
            ),
            "acted_by": (
                {"id": step.acted_by_id.id, "name": step.acted_by_id.name}
                if step.acted_by_id
                else None
            ),
            "acted_date": (
                fields.Datetime.to_string(step.acted_date) if step.acted_date else None
            ),
            "activated_date": (
                fields.Datetime.to_string(step.activated_date)
                if step.activated_date
                else None
            ),
            "note_short": note_short,
            "note_full": note_full or None,
            "is_current": step.state == "active",
        }

    def _build_routing_preview_payload(self, steps):
        """Group steps by ``order`` (Stage) and return the payload shape the
        widget expects. Empty steps → empty stages so a draft doc with no route
        renders "no steps yet" gracefully."""
        self.ensure_one()
        stages_by_order = {}
        for step in steps.sorted(key=lambda s: (s.order, s.id)):
            stages_by_order.setdefault(step.order, []).append(
                self._build_routing_step_payload(step)
            )
        stages = [
            {"order": order, "steps": stage_steps}
            for order, stage_steps in sorted(stages_by_order.items())
        ]
        return {
            "attempt_seq": self.attempt_seq,
            "has_history": self.attempt_seq > 1,
            "stages": stages,
        }

    def _build_archived_attempts_payload(self):
        """Group archived steps by ``attempt_seq`` DESC so the modal lists the
        most recent prior attempt first.  Uses ``archived_step_ids`` which is
        already ``active_test=False`` scoped (see agx_sarabun.sarabun_document)."""
        self.ensure_one()
        by_attempt = {}
        for step in self.archived_step_ids.sorted(
            key=lambda s: (-s.attempt_seq, s.order, s.id)
        ):
            by_attempt.setdefault(step.attempt_seq, []).append(step)
        result = []
        for attempt_seq in sorted(by_attempt.keys(), reverse=True):
            steps = self.env["sarabun.routing.step"].browse(
                [s.id for s in by_attempt[attempt_seq]]
            )
            payload = self._build_routing_preview_payload(steps)
            payload["attempt_seq"] = attempt_seq
            payload["has_history"] = False  # no re-link inside the archive modal
            result.append(payload)
        return result

    def action_open_routing_history(self):
        """Open the archived-attempts modal (ir.actions.client) driven by the
        SarabunRoutingTimeline widget's history link.  Data is pre-rendered here
        so the client fires no extra RPCs when the dialog opens."""
        self.ensure_one()
        from odoo import _
        return {
            "type": "ir.actions.client",
            "tag": "sarabun_routing_timeline_archive",
            "name": _("ประวัติการเดินเรื่อง (%s)") % (self.subject or self.name or ""),
            "params": {
                "doc_id": self.id,
                "attempts": self._build_archived_attempts_payload(),
            },
        }
