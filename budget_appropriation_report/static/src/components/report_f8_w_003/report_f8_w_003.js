/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ReportF8W003 extends Component {
    get reportName() {
        return this.props.action?.name || "สรุปเปรียบเทียบประมาณการรายจ่าย จำแนกตามหน่วยงานและแผนงาน (F8-W-วง-003)";
    }
}

ReportF8W003.template = "budget_appropriation_report.ReportF8W003";

registry.category("actions").add("report_f8_w_003", ReportF8W003);
