/** @odoo-module **/

import {
  Component,
  useState,
  onWillStart,
  useEnv,
  onWillUnmount,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CharField } from "@web/views/fields/char/char_field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { Budget_table } from "../budget_table/budget_table";

export class ExpenseBudgetRenderer extends Component {
  setup() {
    this.orm = useService("orm");
    this.action = useService("action");
    this.env = useEnv();

    this.state = useState(this.initState());
    this._isActive = true;

    this.env.bus.addEventListener("loading-page", this.loadingToggle);
    this.env.bus.addEventListener("fetch", this.updateData);

    onWillUnmount(() => {
      this._isActive = false;
    });

    onWillStart(this.fetchAll);
  }

  initState() {
    return {
      capitalList: [],
      templateId: 0,
      templateName: "",
      templateLines: [],
      mergedLines: [],
      activityList: [],
      selectedActivity: null,
      activity_selected_list: [],
      parentPath: [],
      selectedCode: "",
      planId: 0,
      planLineList: [],
      fundList: [],
      refreshKey: "",
      loading: false,
    };
  }

  async fetchAll() {
    if (!this._isActive) return;

    const templateId = await this.orm.call("budget.plan", "get_id", []);
    this.state.templateId = templateId;

    const [activityList, fundList, structure, budgetPlan] = await Promise.all([
      this.getPlan("activities"),
      this.getPlan("funds"),
      this.getStructureTemplate(templateId),
      this.getBudgetPlan(templateId),
    ]);

    this.state.activityList = activityList;
    this.state.fundList = fundList;
    this.state.templateName = structure.budget_template.name;
    this.state.templateLines = structure.lines.map((line) => ({
      ...line,
      can_edit: line.has_children.length === 0,
      root_parent: line.parent_id
        ? parseInt(line.parent_path.split("/")[0])
        : line.id,
    }));

    this.state.planId = budgetPlan.id;

    await this.fetchPlanLinesAndCapital();
    this.mergeTemplateAndPlan();
  }

  updateData = async () => {
    await this.fetchPlanLinesAndCapital();
    this.mergeTemplateAndPlan();
  };

  async fetchPlanLinesAndCapital() {
    if (!this._isActive) return;

    const [planLines, capitalItems] = await Promise.all([
      this.orm.searchRead(
        "budget.plan.line",
        [["plan_id", "=", this.state.planId]],
        []
      ),
      this.orm.searchRead("capital.expenditure", [], []),
    ]);

    this.state.planLineList = planLines;
    this.state.capitalList = capitalItems;
  }

  loadingToggle = async (ev) => {
    const activity = ev.detail.activity;

    this.state.selectedActivity = activity;
    this.state.parentPath = activity.parent_path.split("/").filter(Boolean);

    const div = document.querySelector(".o_select_budget_plan");
    if (div) {
      div.scrollIntoView({ behavior: "smooth", block: "end" });
    }

    this.state.loading = true;
    await this.getPlan("activities");
    setTimeout(async () => {
      this.state.loading = false;
      await this.fetchAll();
    }, 1000);
  };

  async getPlan(type = "funds") {
    const [plan] = await this.orm.searchRead(
      "account.analytic.plan",
      [["code", "=", type]],
      []
    );
    return await this.orm.searchRead(
      "account.analytic.account",
      [["plan_id", "=", plan.id]],
      []
    );
  }

  async getBudgetPlan(templateId) {
    const [plan] = await this.orm.searchRead(
      "budget.plan",
      [["template_id", "=", templateId]],
      []
    );
    return plan;
  }

  async getStructureTemplate(templateId) {
    return await this.orm.call(
      "report.budget.budget_template_structure",
      "get_html",
      [templateId]
    );
  }

  mergeTemplateAndPlan() {
    const merged = this.state.templateLines.map((templateLine) => {
      const matchedPlanLine = this.state.planLineList.find(
        (pl) => pl.template_line_id?.[0] === templateLine.id
      );

      const relatedCapital = this.state.capitalList.filter(
        (cap) =>
          matchedPlanLine && cap.budget_plan_line_id?.[0] === matchedPlanLine.id
      );

      return {
        ...templateLine,
        plan_line: matchedPlanLine || null,
        capital_expenditures: relatedCapital.length ? relatedCapital : null,
        plan_id: this.state.planId,
      };
    });

    this.state.mergedLines = JSON.parse(JSON.stringify(merged));
    this.state.refreshKey = Date.now();
  }

  async fetchActivityDetails() {
    const result = await this.orm.searchRead(
      "account.analytic.account",
      [["id", "=", this.state.parentPath]],
      []
    );
    this.state.selectedCode = result.map((r) => r.code).join("");
  }

  async onBudgetChange(ev) {
    const selectedId = parseInt(ev.target.value);
    this.env.bus.trigger("budget-type", {
      plan: selectedId,
      budget_plan_id: this.state.planId,
    });
  }
}

ExpenseBudgetRenderer.components = {
  CharField,
  IntegerField,
  Budget_table,
};

ExpenseBudgetRenderer.template = "budget_plan_ui.expense_budget_renderer";
