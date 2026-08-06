/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";

// Fields read from the selected employee to build the detail card.
const DETAIL_FIELDS = ["academic_standing_title", "work_email", "department_id", "kid"];

/**
 * Many2one widget that renders the academic standing title, work email,
 * department (faculty / department) and KID as an icon-prefixed detail card
 * below the field, instead of plain ``name_get`` extra lines.
 *
 * Supports fields pointing to ``hr.employee`` directly, or to ``res.users``
 * (in which case the linked ``employee_id`` is resolved first).
 *
 * Usage: ``<field name="employee_id" widget="employee_detail_many2one"/>``
 */
export class EmployeeDetailMany2OneField extends Many2OneField {
    setup() {
        super.setup();
        this.detail = useState({ data: null });
        onWillStart(() => this.loadDetail(this.props.value));
        onWillUpdateProps((nextProps) => {
            const prevId = this.props.value && this.props.value[0];
            const nextId = nextProps.value && nextProps.value[0];
            if (prevId !== nextId) {
                this.loadDetail(nextProps.value);
            }
        });
    }

    async loadDetail(value) {
        if (!value) {
            this.detail.data = null;
            return;
        }
        let employeeId = value[0];
        if (this.relation === "res.users") {
            const [user = {}] = await this.orm.read(
                "res.users",
                [value[0]],
                ["employee_id"],
                { context: this.context }
            );
            if (!user.employee_id) {
                this.detail.data = null;
                return;
            }
            employeeId = user.employee_id[0];
        }
        const [record = {}] = await this.orm.read("hr.employee", [employeeId], DETAIL_FIELDS, {
            context: this.context,
        });
        let department = false;
        if (record.department_id) {
            const [dept = {}] = await this.orm.read(
                "hr.department",
                [record.department_id[0]],
                ["complete_name", "code"],
                { context: this.context }
            );
            department = dept.code
                ? `[${dept.code || '-'}] ${dept.complete_name}`
                : dept.complete_name;
        }
        this.detail.data = {
            academic_standing_title: record.academic_standing_title,
            work_email: record.work_email,
            department,
            kid: record.kid,
        };
    }

    get employeeDetail() {
        return this.detail.data;
    }
}

EmployeeDetailMany2OneField.template =
    "hr_employee_name_detail_kmitl.EmployeeDetailMany2OneField";

registry.category("fields").add("employee_detail_many2one", EmployeeDetailMany2OneField);
