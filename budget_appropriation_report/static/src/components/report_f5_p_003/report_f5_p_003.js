/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF5P003 extends Component {
    get reportName() {
        return this.props.action?.name || "สรุปประมาณการรายจ่าย (F5-P-วง-003)";
    }
}

ReportF5P003.template = "budget_appropriation_report.ReportF5P003";

registry.category("actions").add("report_f5_p_003", ReportF5P003);
