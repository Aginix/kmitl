/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF9W003 extends Component {
    get reportName() {
        return this.props.action?.name || "สรุปสัดส่วนประมาณการรายจ่าย จําแนกตามหน่วยงาน/แผนงาน/งบรายจ่าย (F9-W-วง-003)";
    }
}

ReportF9W003.template = "budget_appropriation_report.ReportF9W003";

registry.category("actions").add("report_f9_w_003", ReportF9W003);
