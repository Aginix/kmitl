/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF3P005 extends Component {
    get reportName() {
        return this.props.action?.name || "สรุปประมาณการรายรับและรายจ่าย (F3-P-วง-005)";
    }
}

ReportF3P005.template = "budget_appropriation_report.ReportF3P005";

registry.category("actions").add("report_f3_p_005", ReportF3P005);
