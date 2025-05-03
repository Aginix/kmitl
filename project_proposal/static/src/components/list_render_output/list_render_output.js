/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

export class List_render_output extends ListRenderer {
  setup() {
    super.setup();
  }
}

List_render_output.template = "project_proposal.List_render_output";

List_render_output.rowsTemplate = "project_proposal.ListRenderer.Rows";
List_render_output.recordRowTemplate =
  "project_proposal.ListRenderer.RecordRow";

List_render_output.props = [
  "activeActions?",
  "list",
  "archInfo",
  "openRecord",
  "onAdd?",
  "cycleOnTab?",
  "allowSelectors?",
  "editable?",
  "noContentHelp?",
  "nestedKeyOptionalFieldsData?",
  "readonly?",
  "onOptionalFieldsChanged?",
];
