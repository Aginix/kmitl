/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRendererOutput } from "../list_renderer_output/list_renderer_output";

export class TableOutput extends X2ManyField {
  setup() {
    super.setup();
  }
}

TableOutput.props = {
  ...standardFieldProps,
  addLabel: { type: String, optional: true },
  editable: { type: String, optional: true },
};
TableOutput.components = {
  ListRendererOutput,
};
TableOutput.template = "project_kmitl.Table_output";

registry.category("fields").add("table_output", TableOutput);
