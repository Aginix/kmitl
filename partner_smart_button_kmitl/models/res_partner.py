from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # One compute per count: each button is behind its own group, so a user
    # without access to one model must never trigger the other counts.
    disbursement_request_count = fields.Integer(
        string="ใบขอเบิก",
        compute="_compute_disbursement_request_count",
    )
    advance_payment_count = fields.Integer(
        string="สัญญาเงินยืม",
        compute="_compute_advance_payment_count",
    )
    withholding_tax_cert_count = fields.Integer(
        string="ใบหัก ณ ที่จ่าย",
        compute="_compute_withholding_tax_cert_count",
    )
    work_acceptance_count = fields.Integer(
        string="ใบตรวจรับ",
        compute="_compute_work_acceptance_count",
    )
    purchase_guarantee_count = fields.Integer(
        string="หลักประกัน",
        compute="_compute_purchase_guarantee_count",
    )
    purchase_request_approval_count = fields.Integer(
        string="รายงานขอซื้อ/จ้าง",
        compute="_compute_purchase_request_approval_count",
    )

    # -------------------------------------------------------------------------
    # Domains: the contact or any of its child contacts
    # -------------------------------------------------------------------------
    def _disbursement_request_domain(self):
        """ใบขอเบิกที่ผู้ติดต่อเป็นผู้รับเงินในรายการ."""
        return [("line_ids.partner_id", "child_of", self.ids)]

    def _advance_payment_domain(self):
        """สัญญาเงินยืมที่ผู้ติดต่อเป็นผู้ยืม."""
        return [("partner_id", "child_of", self.ids)]

    def _withholding_tax_cert_domain(self):
        """หนังสือรับรองการหักภาษี ณ ที่จ่ายที่ออกให้ผู้ติดต่อ."""
        return [("partner_id", "child_of", self.ids)]

    def _work_acceptance_domain(self):
        """ใบตรวจรับที่ผู้ติดต่อเป็นผู้ขาย."""
        return [("partner_id", "child_of", self.ids)]

    def _purchase_guarantee_domain(self):
        """หลักประกันของผู้ติดต่อ."""
        return [("partner_id", "child_of", self.ids)]

    def _purchase_request_approval_domain(self):
        """รายงานขอซื้อ/จ้าง (พจ.1) ที่ผู้ติดต่อเป็นผู้ขาย."""
        return [("partner_id", "child_of", self.ids)]

    # -------------------------------------------------------------------------
    # Counts: run with the user's own rights (no sudo) so the badge matches
    # what the button opens.
    # -------------------------------------------------------------------------
    def _compute_related_count(self, field_name, model, domain_method):
        Model = self.env[model]
        for partner in self:
            origin = partner._origin
            partner[field_name] = (
                Model.search_count(getattr(origin, domain_method)()) if origin else 0
            )

    def _compute_disbursement_request_count(self):
        self._compute_related_count(
            "disbursement_request_count",
            "disbursement.request",
            "_disbursement_request_domain",
        )

    def _compute_advance_payment_count(self):
        self._compute_related_count(
            "advance_payment_count", "advance.payment", "_advance_payment_domain"
        )

    def _compute_withholding_tax_cert_count(self):
        self._compute_related_count(
            "withholding_tax_cert_count",
            "withholding.tax.cert",
            "_withholding_tax_cert_domain",
        )

    def _compute_work_acceptance_count(self):
        self._compute_related_count(
            "work_acceptance_count", "work.acceptance", "_work_acceptance_domain"
        )

    def _compute_purchase_guarantee_count(self):
        self._compute_related_count(
            "purchase_guarantee_count",
            "purchase.guarantee",
            "_purchase_guarantee_domain",
        )

    def _compute_purchase_request_approval_count(self):
        self._compute_related_count(
            "purchase_request_approval_count",
            "purchase.request.approval",
            "_purchase_request_approval_domain",
        )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def _action_view_related(self, xmlid, domain, name):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        records = self.env[action["res_model"]].search(domain)
        action.update(
            name=name,
            domain=domain,
            context={"create": False},
        )
        if len(records) == 1:
            action.update(views=[(False, "form")], view_mode="form", res_id=records.id)
        return action

    def action_view_disbursement_requests(self):
        return self._action_view_related(
            "disbursement.action_disbursement_request",
            self._disbursement_request_domain(),
            _("ใบขอเบิก: %s", self.display_name),
        )

    def action_view_advance_payments(self):
        return self._action_view_related(
            "advance_payment.action_advance_payment",
            self._advance_payment_domain(),
            _("สัญญาเงินยืม: %s", self.display_name),
        )

    def action_view_withholding_tax_certs(self):
        return self._action_view_related(
            "l10n_th_account_tax.action_withholding_tax_cert_menu",
            self._withholding_tax_cert_domain(),
            _("หนังสือรับรองหัก ณ ที่จ่าย: %s", self.display_name),
        )

    def action_view_work_acceptances(self):
        return self._action_view_related(
            "purchase_work_acceptance.action_work_acceptance",
            self._work_acceptance_domain(),
            _("ใบตรวจรับ: %s", self.display_name),
        )

    def action_view_purchase_guarantees(self):
        return self._action_view_related(
            "l10n_th_gov_purchase_guarantee.purchase_guarantee_action",
            self._purchase_guarantee_domain(),
            _("หลักประกัน: %s", self.display_name),
        )

    def action_view_purchase_request_approvals(self):
        return self._action_view_related(
            "purchase_request_approval.action_purchase_request_approval",
            self._purchase_request_approval_domain(),
            _("รายงานขอซื้อ/จ้าง: %s", self.display_name),
        )
