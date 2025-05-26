/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

export class List_renderer_output extends ListRenderer {
  setup() {
    super.setup();
  }
  freezeColumnWidths() {
  }
}

List_renderer_output.template = "project_proposal.List_render_output";

List_renderer_output.rowsTemplate = "project_proposal.ListRenderer.Rows";
List_renderer_output.recordRowTemplate =
  "project_proposal.ListRenderer.RecordRow";

  List_renderer_output.props = [
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
