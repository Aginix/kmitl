# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    reference = fields.Reference(
        selection_add=[("kmitl.project", "KMITL Project")],
        ondelete={"kmitl.project": "set null"},
    )

    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        compute="_compute_reference_fields",
        store=True,
        index=True,
        tracking=True,
    )

    @api.depends("reference")
    def _compute_reference_fields(self):
        super()._compute_reference_fields()
        for rec in self:
            if rec.reference and rec.reference._name == "kmitl.project":
                rec.kmitl_project_id = rec.reference.id
            else:
                rec.kmitl_project_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records.filtered(lambda r: r.kmitl_project_id):
            rec._link_to_project()
        return records

    def _link_to_project(self):
        """A project-sourced DR draws the project's already-reserved shared
        commitment (budget ADR-0007). Its budget context — the budget
        account, the full analytic distribution (the 4 financial dimensions plus
        the project's own kmitl_project dimension, so the spend is attributed back
        to the project) and the shared commitment — is written here server-side so
        the DR always carries it, even when created programmatically rather than
        through the pre-filled form. Its approval then obligates/consumes the
        project's reservation; many DRs may draw the one commitment, capped by its
        available headroom at approval."""
        self.ensure_one()
        project = self.kmitl_project_id
        commitment = project.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]
        vals = {}
        if self.budget_account_id != project.budget_account_id:
            vals["budget_account_id"] = project.budget_account_id.id
        if commitment and self.budget_commitment_id != commitment:
            vals["budget_commitment_id"] = commitment.id
        project_dist = project.analytic_distribution or False
        if (self.analytic_distribution or False) != project_dist:
            vals["analytic_distribution"] = project_dist
        if vals:
            self.write(vals)
        self._log_created_from_project(project)

    def _log_created_from_project(self, project):
        self.ensure_one()
        dr_link = "/web#id=%d&model=disbursement.request&view_type=form" % self.id
        # sudo: an automated audit note — the DR requester may hold only read on
        # the project (kmitl_project_disbursement_read_rule), while chatter posting
        # defaults to requiring write (_mail_post_access).
        project.sudo().message_post(
            body=_(
                'Disbursement Request <a href="%(link)s" target="_blank">'
                "%(name)s</a> has been created from this project."
            )
            % {"link": dr_link, "name": self.name},
            subtype_xmlid="mail.mt_note",
        )
        project_link = "/web#id=%d&model=kmitl.project&view_type=form" % project.id
        self.message_post(
            body=_(
                'Created from Project <a href="%(link)s" target="_blank">'
                "%(name)s</a>."
            )
            % {"link": project_link, "name": project.display_name},
            subtype_xmlid="mail.mt_note",
        )

    def _is_pooled_commitment(self, commitment):
        """A project's reservation is drawn by many disbursement requests (budget
        ADR-0007), just like a procurement plan's. Cancelling one request must
        therefore reverse only THIS request's obligate/consume lines and leave the
        reservation open for the project and its other documents — even when this
        is the only request linked to it so far."""
        return bool(commitment.kmitl_project_id) or super()._is_pooled_commitment(
            commitment
        )

    def action_view_kmitl_project(self):
        self.ensure_one()
        if not self.kmitl_project_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "view_mode": "form",
            "res_id": self.kmitl_project_id.id,
            "target": "current",
        }
