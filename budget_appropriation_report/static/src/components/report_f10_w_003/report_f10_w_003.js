/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF10W003 extends Component {
    get reportName() {
        return this.props.action?.name || "สรุปประมาณการรายจ่าย จําแนกตามแผนงาน-งานและงบรายจ่าย (F10-W-วง-003)";
    }
}

ReportF10W003.template = "budget_appropriation_report.ReportF10W003";

registry.category("actions").add("report_f10_w_003", ReportF10W003);
