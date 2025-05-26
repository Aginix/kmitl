/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { List_renderer_output } from "../list_renderer_output/list_renderer_output";

export class Table_output extends X2ManyField {
  setup() {
    super.setup();
  }
}

Table_output.props = {
  ...standardFieldProps,
  addLabel: { type: String, optional: true },
  editable: { type: String, optional: true },
};
Table_output.components = {
  List_renderer_output,
};
Table_output.template = "project_proposal.Table_output";

registry.category("fields").add("table_output", Table_output);
