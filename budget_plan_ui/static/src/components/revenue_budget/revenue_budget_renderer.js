/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, useEnv } from "@odoo/owl";
import { Budget_table } from "../budget_table/budget_table";

export class RevenueBudgetRenderer extends Component {
  setup() {
    this.orm = useService("orm");
    this.env = useEnv();
    this.state = useState(this.initState());

    this._isActive = true;
    onWillStart(this.loadData);

    this.env.bus.addEventListener("fetch", this.updateData);
  }

  initState() {
    return {
      budget_plan: { id: 0, data: [] },
      plan_lines: [],
      template: [],
      template_lines: [],
      merged_lines: [],
      refresh_key: "",
    };
  }

  onWillUnmount() {
    this._isActive = false;
  }

  updateData = async () => {
    await this.loadData();
  };

  async loadData() {
    try {
      const templateId = await this.getTemplateId();
      const [plan, planLines, template, templateLines] = await Promise.all([
        this.getPlan(templateId),
        this.getPlanLinesByTemplate(templateId),
        this.getStructureTemplate(templateId, "budget_template"),
        this.getStructureTemplate(templateId, "lines"),
      ]);

      if (!this._isActive) return;

      this.state.budget_plan = { id: plan.id, data: plan };
      this.state.plan_lines = planLines;
      this.state.template = template;

      this.state.template_lines = templateLines.map((line) => ({
        ...line,
        can_edit: line.has_children.length === 0,
      }));

      this.mergePlanAndTemplate();
    } catch (err) {
      console.warn("Load failed:", err);
    }
  }

  mergePlanAndTemplate() {
    const merged = this.state.template_lines.map((templateLine) => {
      const matched = this.state.plan_lines.find(
        (planLine) =>
          (planLine.template_line_id?.[0] || planLine.template_line_id) ===
          templateLine.id
      );
      return {
        ...templateLine,
        plan_line: matched || null,
        plan_id: this.state.budget_plan.id,
      };
    });

    this.state.merged_lines = merged;
    this.state.refresh_key = Date.now();
  }

  async getTemplateId() {
    return await this.orm.call("budget.plan", "get_id", []);
  }

  async getPlan(templateId) {
    const result = await this.orm.searchRead(
      "budget.plan",
      [["template_id", "=", templateId]],
      []
    );
    return result[0];
  }
  
  async getPlanLinesByTemplate(templateId) {
    const plan = await this.getPlan(templateId);
    const lines = await this.orm.searchRead(
      "budget.plan.line",
      [["plan_id", "=", plan.id]],
      []
    );
    return lines;
  }

  async getStructureTemplate(templateId, type) {
    const res = await this.orm.call(
      "report.budget.budget_template_structure",
      "get_html",
      [templateId]
    );
    return res[type];
  }
}
RevenueBudgetRenderer.components = { Budget_table };
RevenueBudgetRenderer.template = "budget_plan_ui.revenue_budget_renderer";
