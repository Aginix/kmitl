/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {getDefaultConfig} from "@web/views/view";
import {BudgetExpenditureReportControlPanel} from "./control_panel";
import {formatFloat} from "@web/views/fields/formatters";
import {Component, EventBus, useSubEnv, onWillStart, useState} from "@odoo/owl";

export class BudgetExpenditureReportMain extends Component {
    setup() {
        this.formatFloat = formatFloat;
        this.orm = useService("orm");
        this.state = useState({
            budgetTemplates: [],
            selectedBudgetTemplateId: undefined,
            report: [],
        });

        useSubEnv({
            config: {
                ...getDefaultConfig(),
                ...this.env.config,
            },
            overviewBus: new EventBus(),
        });

        onWillStart(async () => {
            await this.loadBudgetTemplates();
            await this.loadData();
        });
    }

    async loadData() {
        if (!this.state.selectedBudgetTemplateId) return;

        const args = [
            this.state.selectedBudgetTemplateId,
            ["department_analytic_id", "=", 1],
        ];
        const context = {...this.context};
        const data = await this.orm.call(
            "report.budget.budget_expenditure_report",
            "get_html",
            args,
            {context}
        );

        this.state.report = data;

        return data;
    }

    async loadBudgetTemplates() {
        const data = await this.orm.searchRead(
            "budget.template",
            [["budget_type", "=", "expense"]],
            ["name", "date_range_fy_id", "budget_type"],
            {
                order: `date_range_fy_id DESC`,
            }
        );

        this.state.budgetTemplates = data;

        if (data.length > 0) {
            this.state.selectedBudgetTemplateId = this.state.budgetTemplates[0].id;
        }

        return data;
    }

    //---- Getters ----
    get selectedBudgetTemplate() {
        if (!this.state.selectedBudgetTemplateId) return undefined;
        return this.state.budgetTemplates.find(
            (template) => template.id === this.state.selectedBudgetTemplateId
        );
    }

    async onChangeBudgetTemplate(templateId) {
        this.state.selectedBudgetTemplateId = templateId;
        await this.loadData()
    }
}

BudgetExpenditureReportMain.template = "budget.BudgetExpenditureReportMain";
BudgetExpenditureReportMain.components = {BudgetExpenditureReportControlPanel};
BudgetExpenditureReportMain.props = {};

registry
    .category("actions")
    .add("budget_expenditure_report", BudgetExpenditureReportMain);
