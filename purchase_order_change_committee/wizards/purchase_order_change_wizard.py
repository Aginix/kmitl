from odoo import api, fields, models


class CommitteeWizardLine(models.TransientModel):
    _name = "purchase.order.change.committee.wizard.line"
    _description = "Committee Wizard Line"

    old_wa_wizard_id = fields.Many2one(
        comodel_name="purchase.order.change.wizard",
        ondelete="cascade",
    )
    new_wa_wizard_id = fields.Many2one(
        comodel_name="purchase.order.change.wizard",
        ondelete="cascade",
    )
    old_ws_wizard_id = fields.Many2one(
        comodel_name="purchase.order.change.wizard",
        ondelete="cascade",
    )
    new_ws_wizard_id = fields.Many2one(
        comodel_name="purchase.order.change.wizard",
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        required=True,
    )
    approve_role = fields.Selection(
        selection=[
            ("chairman", "Chairman"),
            ("committee", "Committee"),
            ("secretary", "Secretary"),
        ],
        string="Role",
        required=True,
        default="committee",
    )


class PurchaseOrderChangeWizard(models.TransientModel):
    _inherit = "purchase.order.change.wizard"

    show_wa_committee = fields.Boolean()
    show_ws_committee = fields.Boolean()

    old_wa_committee_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.wizard.line",
        inverse_name="old_wa_wizard_id",
        string="WA Committee (Before)",
    )
    new_wa_committee_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.wizard.line",
        inverse_name="new_wa_wizard_id",
        string="WA Committee (After)",
    )
    old_ws_committee_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.wizard.line",
        inverse_name="old_ws_wizard_id",
        string="Work Supervisor (Before)",
    )
    new_ws_committee_ids = fields.One2many(
        comodel_name="purchase.order.change.committee.wizard.line",
        inverse_name="new_ws_wizard_id",
        string="Work Supervisor (After)",
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)

        default_section_ids = self.env.context.get("default_section_ids")
        if default_section_ids and isinstance(default_section_ids, list):
            ids = default_section_ids[0][2]
        else:
            ids = []

        sections = self.env["purchase.change.section"].browse(ids)
        xml_ids_map = sections.get_external_id()
        xml_id_list = [xml.split(".")[-1] for xml in xml_ids_map.values()]

        show_wa = "purchase_change_section_wa_committee" in xml_id_list
        show_ws = "purchase_change_section_work_supervisor" in xml_id_list
        vals["show_wa_committee"] = show_wa
        vals["show_ws_committee"] = show_ws

        purchase = self.env["purchase.order"].browse(
            self.env.context.get("default_purchase_id")
        )
        if purchase:
            if show_wa:
                committee_vals = [
                    (0, 0, {
                        "employee_id": c.employee_id.id,
                        "approve_role": c.approve_role,
                    })
                    for c in purchase.work_acceptance_committee_ids
                ]
                vals["old_wa_committee_ids"] = committee_vals
                vals["new_wa_committee_ids"] = [
                    (0, 0, {
                        "employee_id": c.employee_id.id,
                        "approve_role": c.approve_role,
                    })
                    for c in purchase.work_acceptance_committee_ids
                ]
            if show_ws:
                supervisor_vals = [
                    (0, 0, {
                        "employee_id": c.employee_id.id,
                        "approve_role": c.approve_role,
                    })
                    for c in purchase.work_supervisor_ids
                ]
                vals["old_ws_committee_ids"] = supervisor_vals
                vals["new_ws_committee_ids"] = [
                    (0, 0, {
                        "employee_id": c.employee_id.id,
                        "approve_role": c.approve_role,
                    })
                    for c in purchase.work_supervisor_ids
                ]

        return vals

    def action_save_changes(self):
        self._save_committee_changes()
        return super().action_save_changes()

    def _save_committee_changes(self):
        self.ensure_one()
        po = self.purchase_id.sudo()

        if self.show_wa_committee:
            self._save_and_apply_committee(
                po,
                "work_acceptance",
                self.old_wa_committee_ids,
                self.new_wa_committee_ids,
                po.work_acceptance_committee_ids,
            )

        if self.show_ws_committee:
            self._save_and_apply_committee(
                po,
                "work_supervisor",
                self.old_ws_committee_ids,
                self.new_ws_committee_ids,
                po.work_supervisor_ids,
            )

    def _save_and_apply_committee(
        self, po, committee_type, old_lines, new_lines, po_committee
    ):
        Snapshot = self.env["purchase.order.change.committee.snapshot"].sudo()

        for line in old_lines:
            Snapshot.create({
                "change_id": self.change_id.id,
                "committee_type": committee_type,
                "snapshot_type": "before",
                "employee_id": line.employee_id.id,
                "approve_role": line.approve_role,
            })

        for line in new_lines:
            Snapshot.create({
                "change_id": self.change_id.id,
                "committee_type": committee_type,
                "snapshot_type": "after",
                "employee_id": line.employee_id.id,
                "approve_role": line.approve_role,
            })

        po_committee.unlink()
        for line in new_lines:
            self.env["procurement.committee"].sudo().create({
                "purchase_order_id": po.id,
                "employee_id": line.employee_id.id,
                "approve_role": line.approve_role,
                "committee_type": committee_type,
                "name": line.employee_id.display_name,
            })
