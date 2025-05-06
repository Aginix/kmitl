/** @odoo-module **/

import { Component, useEnv, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Budget_tree_modal extends Component {
  setup() {
    this.orm = useService("orm");
    this.env = useEnv();

    this.state = useState(this.getInitialState());

    this.env.bus.addEventListener("capital", this.onCapitalEvent);
    this.env.bus.addEventListener("modal", this.onModalEvent);
    this.env.bus.addEventListener("budget-type", this.onChangePlan);
  }

  getInitialState() {
    return {
      modalMode: "create",
      capital: {},
      budget_plan: {
        plan: 0,
        budget_plan_id: 0,
        budget_plan_line_id: 0,
        budget_plan_line_modal: [],
      },
      budget_template: {
        budget_template_line_id: 0,
      },
    };
  }

  onCapitalEvent = (ev) => {
    const capital = ev.detail.capital;
    this.state.budget_template.budget_template_line_id = capital.id;

    if (capital.plan_line) {
      this.state.budget_plan.budget_plan_line_modal =
        capital.capital_expenditures;
      this.state.budget_plan.budget_plan_line_id = capital.plan_line.id;
    } else {
      this.state.budget_plan.budget_plan_line_modal = [];
      this.state.budget_plan.budget_plan_line_id = 0;
    }
  };

  onChangePlan = (ev) => {
    const { plan, budget_plan_id } = ev.detail;
    this.state.budget_plan.plan = plan;
    this.state.budget_plan.budget_plan_id = budget_plan_id;
  };

  refresh() {
    this.env.bus.trigger("fetch", {});
  }

  sendEvent() {
    this.env.bus.trigger("modal_event", {
      capital: this.state.capital,
      mode: this.state.modalMode,
    });
  }

  openModal(mode, capital = null) {
    this.state.modalMode = mode;
    this.state.capital =
      mode === "edit" && capital
        ? { ...capital, capital_id: capital.id, payment_plan: "single" }
        : this.getEmptyCapital();

    this.sendEvent();
    $("#capital_modal").modal("show");
  }

  getEmptyCapital() {
    return {
      name: "",
      expected_purchase_date: "",
      note: "",
      payment_plan: "single",
      amount: 0,
    };
  }

  onModalEvent = async ({ detail }) => {
    this.state.capital = { ...detail.capital };
    this.state.capital.capital_id = detail.capital.capital_id;

    if (this.state.modalMode === "edit") {
      await this.editCapital();
    } else {
      await this.saveCapital();
    }

    if (!this.__owl__.isDestroyed) {
      this.refresh();
    }
  };

  async saveCapital() {
    try {
      const {
        capital,
        budget_plan: { budget_plan_id, budget_plan_line_id },
        budget_template: { budget_template_line_id },
      } = this.state;

      const plan_line_id = budget_plan_line_id;

      const newPlanLineId = await this.orm.create("budget.plan.line", [
        {
          plan_id: budget_plan_id,
          template_line_id: budget_template_line_id,
          amount: 0,
        },
      ]);

      await this.orm.create("capital.expenditure", [
        {
          name: capital.name,
          expected_purchase_date: capital.expected_purchase_date || null,
          amount: capital.amount,
          note: capital.note,
          budget_plan_line_id: plan_line_id,
          payment: "single",
        },
      ]);

      if (!this.__owl__.isDestroyed) {
        $("#capital_tree").modal("hide");
      }
    } catch (error) {
      console.warn("Error saving capital:", error);
    }
  }

  async editCapital() {
    try {
      const { capital } = this.state;

      if (this.__owl__.isDestroyed) return;

      await this.orm.write("capital.expenditure", [capital.capital_id], {
        name: capital.name,
        expected_purchase_date: capital.expected_purchase_date,
        amount: capital.amount,
        note: capital.note,
      });

      if (!this.__owl__.isDestroyed) {
        $("#capital_tree").modal("hide");
      }
    } catch (error) {
      console.warn("Error editing capital:", error);
    }
  }

  async deleteCapital(capital) {
    try {
      if (this.__owl__.isDestroyed) return;

      await this.orm.unlink("capital.expenditure", [capital.id]);

      if (!this.__owl__.isDestroyed) {
        this.refresh();
      }
    } catch (error) {
      console.warn("Error deleting capital:", error);
    }
  }
}

Budget_tree_modal.template = "budget_plan_ui.Budget_tree_modal";
