/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Component, useState, onWillStart, useEnv, onWillUnmount} from "@odoo/owl";
import {Budget_control_panel} from "../budget_control_panel/budget_control_panel";
import {NoteEditor} from "../note_editor/note_editor";

export class Revenue_budget extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            budget_plan: {
                budget_plan_data: [],
                budget_plan_department_name: "",
                budget_plan_merge: [],
            },
            noteValue: "",
            budget_plan_line: {
                budget_plan_line_data: [],
                budget_plan_line_amount: {},
                budget_plan_line_note: {},
            },
            budget_template: {
                budget_template_data: [],
            },
            budget_template_line: {
                budget_template_line_data: [],
                budget_template_merge: [],
            },
            toggle: {
                note: {},
            },
            formated: {
                amount: {},
            },
            fund: 0,
        });
        onWillStart(async () => {
            await this.fetchData();
            await this.mergeData();
            await this.generateState();
        });
    }

    formattedAmount(value) {
        return new Intl.NumberFormat("en-US").format(value);
    }

    parseNumber(value) {
        if (!value) return 0;
        return parseInt(value.toString().replace(/,/g, ""), 10) || 0;
    }

    updateNote = async (note, data) => {
        if (!data.plan_line) {
            await this.orm.create("budget.plan.line", [
                {
                    plan_id: this.state.budget_plan.budget_plan_data.id,
                    fund_analytic_id: this.state.fund,
                    note: note,
                    template_line_id: data.id,
                },
            ]);
        } else {
            await this.orm.write("budget.plan.line", [data.plan_line.id], {
                fund_analytic_id: this.state.fund,
                note: note,
            });
        }
        await this.fetchData();
        await this.generateState();
    };

    async mergeData() {
        const mergeData = this.state.budget_template_line.budget_template_line_data.map(
            (templateLine) => {
                const matchingPlanLine =
                    this.state.budget_plan_line.budget_plan_line_data.find(
                        (planLine) => planLine.template_line_id[0] === templateLine.id
                    );
                return {
                    ...templateLine,
                    plan_line: matchingPlanLine || null,
                };
            }
        );
        this.state.budget_template_line.budget_template_merge = mergeData;
    }

    async generateState() {
        const data = this.state.budget_template_line.budget_template_merge.map(
            (data) => {
                if (data.plan_line) {
                    this.state.budget_plan_line.budget_plan_line_amount[
                        `${data.plan_line.id}-${data.id}`
                    ] = data.plan_line.amount;
                    this.state.formated.amount[`${data.plan_line.id}-${data.id}`] =
                        this.formattedAmount(data.plan_line.amount);
                    this.state.budget_plan_line.budget_plan_line_note[
                        `${data.plan_line.id}-${data.id}`
                    ] = data.plan_line.note;
                }
                return data.id;
            }
        );
    }

    async toggleNote(pos) {
        const key = `${pos.id}-${pos.code}`;
        this.state.toggle.note[key] = !this.state.toggle.note[key];
    }

    onBlurSavePlan = async (pos) => {
        const data = await this.orm.write("budget.plan.line", [pos.plan_line.id], {
            fund_analytic_id: this.state.fund,
            amount: this.parseNumber(
                this.state.formated.amount[`${pos.plan_line.id}-${pos.id}`]
            ),
        });
        this.state.formated.amount[`${pos.plan_line.id}-${pos.id}`] =
            this.formattedAmount(
                this.state.formated.amount[`${pos.plan_line.id}-${pos.id}`]
            );
        await this.fetchData();
        await this.generateState();
    };

    onBlurSaveCreate = async (pos) => {
        await this.orm.create("budget.plan.line", [
            {
                plan_id: this.state.budget_plan.budget_plan_data.id,
                fund_analytic_id: this.state.fund,
                template_line_id: pos.id,
                amount: this.parseNumber(
                    this.state.formated.amount[`${pos.code}-${pos.id}`]
                ),
            },
        ]);
        this.state.formated.amount[`${pos.code}-${pos.id}`] = this.formattedAmount(
            this.state.formated.amount[`${pos.code}-${pos.id}`]
        );
        await this.fetchData();
        await this.generateState();
    };

    async fetchData() {
        const budget_template_id = await this.orm.call("budget.plan", "get_id", []);

        const budget_plan_id = await this.orm.searchRead(
            "budget.plan",
            [["template_id", "=", budget_template_id]],
            []
        );
        this.state.budget_plan.budget_plan_data = budget_plan_id[0];
        this.state.fund = budget_plan_id[0].source_analytic_id[0];
        this.state.budget_plan.budget_plan_department_name = "";

        const budget_plan_line_id = await this.orm.searchRead(
            "budget.plan.line",
            [["plan_id", "=", this.state.budget_plan.budget_plan_data.id]],
            []
        );
        this.state.budget_plan_line.budget_plan_line_data = budget_plan_line_id;

        const get_structure_template_line = await this.orm.call(
            "report.budget.budget_template_structure",
            "get_html",
            [budget_template_id]
        );
        this.state.budget_template.budget_template_data =
            get_structure_template_line["budget_template"];
        const budget_template_line_can_edit = get_structure_template_line["lines"].map(
            (item) => ({
                ...item,
                can_edit: item.has_children.length === 0,
            })
        );
        this.state.budget_template_line.budget_template_line_data =
            budget_template_line_can_edit;

        await this.mergeData();
    }
}
Revenue_budget.template = "budget_plan_ui.revenue_budget";
Revenue_budget.components = {Budget_control_panel, NoteEditor};
registry.category("actions").add("revenue_budget", Revenue_budget);
