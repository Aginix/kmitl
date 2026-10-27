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
        preview HTML, then roll back every change. The savepoint guarantees no
        DB side-effect leaks out (``mail.thread`` tracking rows, state
        transitions, snapshot writes — all vanish on rollback)."""
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

    def _apply_simulated_vals(self):
        """Stamp the step as if the user had just acted. Only the fields the
        endorsement block + document preview actually read are set — we don't
        re-run ``act_on_step`` so the preview never triggers origin callbacks,
        stage advancement, number issuance or signed-PDF freezing. For positive
        signature-visible verbs we also snapshot the signer identity so the
        preview shows the acting user's name / position / ลายเซ็น just like the
        real sign would (ADR-0009)."""
        self.ensure_one()
        step = self.step_id.sudo()
        user = self.env.user
        now = fields.Datetime.now()
        vals = {
            "state": "done",
            "disposition": self.disposition,
            "acted_by_id": user.id,
            "acted_date": now,
            "note": self.note or step.note,
        }
        if self.disposition in POSITIVE_DISPOSITIONS and step.verb.show_signature:
            capacity = self.signed_as_position_id or step.position_id
            employee = user.sudo().employee_id
            vals.update(
                {
                    "signed_as_position_id": capacity.id if capacity else False,
                    "signed_name": employee.name or user.name,
                    "signed_position_name": (capacity and capacity.name) or "",
                    "signed_signature": employee.signature or False,
                }
            )
        step.write(vals)
