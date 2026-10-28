"""Simulated PDF preview for the Act-on-Step wizard.

Renders — before the actor clicks ยืนยัน — the exact HTML/PDF the document
will produce once this disposition is confirmed, by applying the step's
"done" state inside a Postgres SAVEPOINT, calling the standard report
pipeline (``sarabun.document._render_preview_html``), then rolling back
every mutation. The result is embedded as an isolated iframe via srcdoc,
so the report's own styles cannot leak into the wizard form.
"""

import logging
from html import escape as html_escape

from markupsafe import Markup

from odoo import api, fields, models

from odoo.addons.agx_sarabun.models.sarabun_routing_step import POSITIVE_DISPOSITIONS

_logger = logging.getLogger(__name__)


class SarabunStepActWizard(models.TransientModel):
    _inherit = "sarabun.step.act.wizard"

    preview_html = fields.Html(
        string="ตัวอย่างเอกสารหลังการดำเนินการ",
        compute="_compute_preview_html",
        sanitize=False,
    )

    @api.depends(
        "step_id",
        "disposition",
        "signed_as_position_id",
        "note",
    )
    def _compute_preview_html(self):
        for wiz in self:
            wiz.preview_html = wiz._build_preview_iframe()

    # ---------------------------------------------------------------- iframe
    def _build_preview_iframe(self):
        self.ensure_one()
        if not self.step_id or not self.disposition:
            return False
        try:
            html = self._render_simulated_html()
        except Exception as exc:  # pragma: no cover — defensive
            _logger.exception("sarabun act preview failed")
            return Markup(
                "<div class='alert alert-warning'>ไม่สามารถสร้างตัวอย่างได้: %s</div>"
            ) % str(exc)
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        srcdoc = html_escape(html, quote=True)
        return Markup(
            '<iframe srcdoc="%s" '
            'style="width:100%%; height:70vh; border:1px solid #ced4da; '
            'border-radius:4px; background:#d9d9d9;"></iframe>'
        ) % Markup(srcdoc)

    # ------------------------------------------------------------- simulation
    def _render_simulated_html(self):
        """Simulate the chosen disposition on the step, render the document's
        preview HTML, then roll back every change. The savepoint undoes the SQL
        (state transitions, snapshot writes); the ORM cache still holds the
        simulated values afterwards, so it is invalidated for the touched models."""
        self.ensure_one()
        cr = self.env.cr
        cr.execute("SAVEPOINT sarabun_act_preview")
        try:
            self._apply_simulated_vals()
            self.env.flush_all()
            return self.step_id.document_id._render_preview_html()
        finally:
            cr.execute("ROLLBACK TO SAVEPOINT sarabun_act_preview")
            cr.execute("RELEASE SAVEPOINT sarabun_act_preview")
            # Not invalidate_all(): it would also wipe the onchange record's values.
            self.env["sarabun.routing.step"].invalidate_model(flush=False)
            self.env["sarabun.document"].invalidate_model(flush=False)

    def _apply_simulated_vals(self):
        """Stamp the step as if the user had just acted. Only the fields the
        endorsement block + document preview actually read are set — we don't
        re-run ``act_on_step`` so the preview never triggers origin callbacks,
        stage advancement, number issuance or signed-PDF freezing. For positive
        signature-visible verbs we also snapshot the signer identity so the
        preview shows the acting user's name / position / ลายเซ็น just like the
        real sign would (ADR-0009)."""
        self.ensure_one()
        # tracking_disable: a tracked write queues a precommit chatter message that
        # the SAVEPOINT rollback would not undo.
        step = self.step_id.sudo().with_context(tracking_disable=True)
        user = self.env.user
        vals = {
            "state": "done",
            "disposition": self.disposition,
            "acted_by_id": user.id,
            "acted_date": fields.Datetime.now(),
            "note": self.note or step.note,
        }
        if self.disposition in POSITIVE_DISPOSITIONS and step.verb.show_signature:
            capacity = self.signed_as_position_id or step.position_id
            vals["signed_as_position_id"] = capacity.id
            vals.update(step._signature_snapshot_vals(user, capacity))
        step.write(vals)
