/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF7W003 extends Component {
    get reportName() {
        return this.props.action?.name || "สรุปเปรียบเทียบประมาณการรายจ่าย จําแนกตามงบรายจ่าย (F7-W-วง-003)";
    }
}

ReportF7W003.template = "budget_appropriation_report.ReportF7W003";

registry.category("actions").add("report_f7_w_003", ReportF7W003);
