/** @odoo-module **/
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {ControlPanel} from "@web/search/control_panel/control_panel";
import {Component, useState, onWillStart} from "@odoo/owl";

export class BudgetTemplateStructure extends Component {
    setup() {
        this.controlPanelDisplay = {
            "top-right": false,
            "bottom-right": false,
        };

        this.state = useState({
            data: {},
        });
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            await this.getData();
        });
    }

    async getData() {
        const args = [this.activeId];
        const context = {...this.context};
        const result = await this.orm.call(
            "report.budget.budget_template_structure",
            "get_html",
            args,
            {context}
        );
        this.state.data = result["lines"];
        this.state.budget_template = result["budget_template"];
        return result;
    }

    //---- Getters ----

    get data() {
        return this.state.data;
    }

    get budget_template() {
        return this.state.budget_template;
    }

    get activeId() {
        return this.props.action.context.active_id;
    }

    get context() {
        return this.props.action.context;
    }
}

BudgetTemplateStructure.template = "budget.BudgetTemplateStructure";
BudgetTemplateStructure.components = {ControlPanel};
BudgetTemplateStructure.props = {};

registry.category("actions").add("budget_template_structure", BudgetTemplateStructure);
