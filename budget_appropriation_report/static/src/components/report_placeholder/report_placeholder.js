/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportPlaceholder extends Component {
    get reportName() {
        return this.props.action?.name || "รายงาน";
    }
}

ReportPlaceholder.template = "budget_appropriation_report.ReportPlaceholder";

const reports = [
    "report_f2_w_003",
    "report_f3_p_005",
    "report_f7_w_003",
    "report_f5_p_003",
    "report_f5_w_003",
    "report_f8_w_003",
    "report_f9_w_003",
    "report_f10_w_003",
];

reports.forEach((tag) => registry.category("actions").add(tag, ReportPlaceholder));
