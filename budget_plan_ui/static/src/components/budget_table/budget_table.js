/** @odoo-module **/

import { Component, useState, useEnv, onWillStart } from "@odoo/owl";
import { NoteEditor } from "../note_editor/note_editor";
import { useService } from "@web/core/utils/hooks";
import { Budget_form_modal } from "../budget_modal/budget_form_modal";
import { Budget_tree_modal } from "../budget_modal/budget_tree_modal";

export class Budget_table extends Component {
  setup() {
    this.state = useState(this.initState());

    this.orm = useService("orm");
    this.env = useEnv();

    this.env.bus.addEventListener("budget-type", this.onChangePlan);

    onWillStart(this.generateState);
  }

  initState() {
    return {
      localData: [...this.props.data],
      rotated: {},
      activity: { select_activity: 0 },
      budget_plan: { plan: 0, budget_plan_id: 0 },
      budget_plan_line: { amount: {}, note: {} },
      formated: { amount: {} },
    };
  }

  getInputProps(template) {
    const hasPlanLine = !!template.plan_line;
    const key = hasPlanLine
      ? `${template.plan_line.id}-${template.id}`
      : `${template.code}-${template.id}`;
    return {
      key,
      mode: hasPlanLine ? "update" : "create",
      value: this.state.formated.amount[key],
      disabled: !template.can_edit,
      modelValue: this.state.formated.amount[key],
      inputValue: hasPlanLine
        ? this.formatAmount(
            this.state.budget_plan_line.amount[key] || template.plan_line.amount
          )
        : undefined,
    };
  }

  async generateState() {
    this.props.data.forEach((data) => {
      if (data.plan_line) {
        const key = `${data.plan_line.id}-${data.id}`;
        this.state.budget_plan_line.amount[key] = data.plan_line.amount;
        this.state.budget_plan_line.note[key] = data.plan_line.note;
        this.state.formated.amount[key] = this.formatAmount(
          data.plan_line.amount
        );
      }
    });
  }

  async modalCapital(template) {
    this.env.bus.trigger("capital", { capital: template });
  }

  onChangePlan = async (ev) => {
    const data = ev.detail;
    this.state.budget_plan.plan = data.plan;
    this.state.budget_plan.budget_plan_id = data.budget_plan_id;
  };

  formatAmount(value) {
    return new Intl.NumberFormat("en-US").format(value);
  }

  parseNumber(value) {
    if (!value) return 0;
    return parseInt(value.toString().replace(/,/g, ""), 10) || 0;
  }

  refresh() {
    this.env.bus.trigger("fetch", {});
  }

  async toggleRotate(key) {
    this.state.rotated[key] = !this.state.rotated[key];
  }

  loadingToggle = async (activity) => {
    this.state.activity.select_activity = activity.id;
    this.env.bus.trigger("loading-page", { activity: activity });
  };

  updateNote = async (note, data) => {
    if (!data.plan_line) {
      await this.orm.create("budget.plan.line", [
        {
          plan_id: data.plan_id,
          note: note,
          template_line_id: data.id,
        },
      ]);
    } else {
      await this.orm.write("budget.plan.line", [data.plan_line.id], {
        note: note,
      });
    }
    this.refresh();
  };

  onBlurSave = async (template, mode) => {
    if (mode == "create") {
      const plan_line_id = await this.orm.create("budget.plan.line", [
        {
          plan_id: template.plan_id,
          activity_analytic_id: this.state.activity.select_activity,
          fund_analytic_id: "",
          template_line_id: template.id,
          amount: this.parseNumber(
            this.state.formated.amount[`${template.code}-${template.id}`]
          ),
        },
      ]);
      this.refresh();
      this.state.formated.amount[`${template.code}-${template.id}`] =
        this.formatAmount(
          this.state.formated.amount[`${template.code}-${template.id}`]
        );
    } else {
      await this.orm.write("budget.plan.line", [template.plan_line.id], {
        amount: this.parseNumber(
          this.state.formated.amount[`${template.plan_line.id}-${template.id}`]
        ),
      });
      this.state.formated.amount[`${template.plan_line.id}-${template.id}`] =
        this.formatAmount(
          this.state.formated.amount[`${template.plan_line.id}-${template.id}`]
        );
      this.refresh();
    }
  };
}

Budget_table.defaultProps = {
  type: "activity",
};

Budget_table.props = {
  data: { type: Object },
  isShow: { type: Boolean, optional: true },
  type: { type: String, optional: true },
};

Budget_table.components = {
  NoteEditor,
  Budget_tree_modal,
  Budget_form_modal,
};

Budget_table.template = "budget_plan_ui.Budget_table";
