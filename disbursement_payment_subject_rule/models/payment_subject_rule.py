# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementPaymentSubjectRule(models.Model):
    """Rule that picks the payment subject (เรื่องที่จ่าย) of a payee's payment line.

    A payment line without a subject is matched against these rules (ordered by
    ``sequence``) and the first matching rule's subject is set on it. Matching is
    advisory: it only pre-fills the subject, which the auditor may still change
    while it is theirs to choose.
    """

    _name = "disbursement.payment.subject.rule"
    _description = "Disbursement Payment Subject Rule"
    _order = "sequence, id"
    _rec_name = "payment_subject_id"

    # Hierarchical dimension criteria, matched over the whole ancestor subtree.
    # An empty criterion behaves as a wildcard (matches any value there).
    _CRITERIA = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # -- criteria: empty = wildcard --------------------------------------
    # ``ondelete="restrict"`` prevents a rule from silently turning into a
    # wildcard when the referenced record is removed.
    partner_type_id = fields.Many2one(
        "res.partner.type",
        string="Payee Type",
        ondelete="restrict",
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "sources")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "activities")],
    )
    # The selection of ``disbursement.request.line.payment_type``, add-ons included.
    payment_type = fields.Selection(
        selection="_selection_payment_type",
        string="Payment Type",
    )

    payment_subject_id = fields.Many2one(
        "kmitl.payment.subject",
        string="Payment Subject",
        required=True,
        ondelete="restrict",
    )

    @api.model
    def _selection_payment_type(self):
        field = self.env["disbursement.request.line"]._fields["payment_type"]
        return field._description_selection(self.env)

    @api.model
    def _find_for_payment_line(self, payment_line):
        """Return the first rule (by sequence) matching ``payment_line``.

        Dimensions come from the request; hierarchical ones match on the whole
        ancestor subtree, as ``finance.assignment.rule`` does: a rule set on a
        parent account covers requests on any of its descendants. Payee type and
        payment type come from the request lines the bill was made from, and
        match on equality when those lines share one; otherwise only the rules
        leaving the criterion blank match.
        """
        request = payment_line.request_id
        lines = (
            payment_line.bill_id.invoice_line_ids.disbursement_request_line_id
            or request._product_lines().filtered(
                lambda ln: ln.partner_id == payment_line.partner_id
            )
        )
        domain = [("active", "=", True)]
        for field in self._CRITERIA:
            ancestors = [
                int(i)
                for i in (request[field].parent_path or "").strip("/").split("/")
                if i
            ]
            domain.append((field, "in", ancestors + [False]))
        partner_types = lines.partner_type_id
        domain.append(
            (
                "partner_type_id",
                "in",
                (partner_types.ids if len(partner_types) == 1 else []) + [False],
            )
        )
        payment_types = set(lines.mapped("payment_type"))
        domain.append(
            (
                "payment_type",
                "in",
                (list(payment_types) if len(payment_types) == 1 else []) + [False],
            )
        )
        return self.search(domain, limit=1)
