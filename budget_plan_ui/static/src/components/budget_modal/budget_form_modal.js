/** @odoo-module **/

import { Component, useState, useEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Budget_form_modal extends Component {
  setup() {
    this.orm = useService("orm");
    this.env = useEnv();

    this.state = useState(this.getInitialState());

    this.env.bus.addEventListener("modal_event", this.onModalEvent);
  }

  getInitialState() {
    return {
      modalMode: "create",
      capital: this.getEmptyCapital(),
    };
  }

  getEmptyCapital() {
    return {
      capital_id: 0,
      name: "",
      expected_purchase_date: "",
      payment_plan: "single",
      note: "",
      amount: 0,
    };
  }

  onModalEvent = ({ detail }) => {
    const { capital, mode } = detail;
    this.state.capital = { ...capital };
    this.state.modalMode = mode || "create";
  };

  sendEvent = () => {
    this.env.bus.trigger("modal", {
      capital: this.state.capital,
      mode: this.state.modalMode,
    });
  };
}

Budget_form_modal.template = "budget_plan_ui.Budget_form_modal";
