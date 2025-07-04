/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";

export class ListRendererOutput extends ListRenderer {
  setup() {
    super.setup();
  }
  freezeColumnWidths() {
  }
}

ListRendererOutput.template = "project_kmitl.List_render_output";

ListRendererOutput.rowsTemplate = "project_kmitl.ListRenderer.Rows";
ListRendererOutput.recordRowTemplate =
  "project_kmitl.ListRenderer.RecordRow";

  ListRendererOutput.props = [
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
