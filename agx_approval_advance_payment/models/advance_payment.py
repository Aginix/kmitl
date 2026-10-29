from odoo import api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "approval_request_id.name"]

    # Typed mirror of `reference`, for searching, grouping and FK integrity:
    # compute for display, inverse for programmatic input. `reference` stays
    # the source of truth (ADR-0007); the borrower names the request by its
    # number (`reference_number`, advance_payment ADR-0029).
    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        compute="_compute_approval_request_id",
        inverse="_inverse_approval_request_id",
        store=True,
        readonly=False,
        index=True,
        ondelete="restrict",
        compute_sudo=False,
        copy=False,
    )

    approval_request_count = fields.Integer(
        compute="_compute_approval_request_count",
    )

    # Read by excep_ar_not_approved (ADR-0030). sudo: the borrower, or the
    # endorser the rule runs as, usually cannot read the request.
    is_approval_request_approved = fields.Boolean(
        compute="_compute_is_approval_request_approved",
        compute_sudo=True,
        help="Technical flag read by the approved-source exception rule.",
    )

    reference = fields.Reference(
        selection_add=[("approval.request", "Approval Request")],
    )

    # Its own compute, not an extension of core's _compute_reference: Odoo
    # protects every field of a compute group while one of them is inverted,
    # so sharing it left reference_model stale after the picker wrote
    # `reference` — and excep_missing_reference fired on a picked request.
    @api.depends("reference")
    def _compute_approval_request_id(self):
        for rec in self:
            ref = rec.reference
            rec.approval_request_id = (
                ref if ref and ref._name == "approval.request" else False
            )

    def _inverse_approval_request_id(self):
        """Picking a request writes it into `reference`, the source of truth."""
        for rec in self:
            if rec.approval_request_id:
                rec.reference = rec.approval_request_id
            elif rec.reference_model == "approval.request":
                rec.reference = False

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        """Drop the mirror too when the new type does not take approval
        requests."""
        super()._onchange_loan_type_id()
        if self.loan_type_id.reference_model != "approval.request":
            self.approval_request_id = False

    def _prepare_vals_from_reference(self):
        """Pull what the request can tell us. The amount is deliberately NOT
        prefilled from the request total: each borrower declares their own
        (ADR-0003)."""
        vals = super()._prepare_vals_from_reference()
        # sudo: the borrower usually cannot read the request (ADR-0029).
        ar = self.approval_request_id.sudo()
        if ar:
            vals.update(
                {
                    "loan_reason": ar.description or "",
                }
            )
        return vals

    def _get_reference_summary(self):
        summary = super()._get_reference_summary()
        ar = self.approval_request_id.sudo()
        if ar:
            summary.update(
                subject=(ar.description or "").strip().split("\n")[0] or ar.name,
                unit=ar.requesting_department_id.display_name,
            )
        return summary

    @api.depends("approval_request_id.state")
    def _compute_is_approval_request_approved(self):
        for rec in self:
            rec.is_approval_request_approved = (
                rec.approval_request_id.state == "approved"
            )

    # Counted as the reader: a borrower who may not open the request sees no
    # button rather than one that opens an AccessError (ADR-0029).
    @api.depends("approval_request_id")
    @api.depends_context("uid")
    def _compute_approval_request_count(self):
        Request = self.env["approval.request"]
        can_read = Request.check_access_rights("read", raise_exception=False)
        for rec in self:
            rec.approval_request_count = (
                Request.search_count([("id", "=", rec.approval_request_id.id)])
                if can_read and rec.approval_request_id
                else 0
            )

    def action_view_approval_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
