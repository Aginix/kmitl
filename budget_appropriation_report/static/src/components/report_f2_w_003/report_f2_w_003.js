/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF2W003 extends Component {
    get reportName() {
        return this.props.action?.name || "จําแนกตามประเภท (F2-W-วง-003)";
    }
}

ReportF2W003.template = "budget_appropriation_report.ReportF2W003";

registry.category("actions").add("report_f2_w_003", ReportF2W003);
