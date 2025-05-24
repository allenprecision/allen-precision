/** @odoo-module alias=theme_alan.SnippetBox **/

// import { useWowlService } from '@web/legacy/utils';
import { Dialog } from "@web/core/dialog/dialog";
import { SnippetPicker } from "theme_alan.SnippetPicker";

const { Component, onRendered, useSubEnv, xml } = owl;

class SnippetBoxDialog extends Dialog {}
SnippetBoxDialog.props = {
    ...Dialog.props,
    size: { type: String, optional: true, validate: (s) => ["sm", "md", "lg", "xl" ,"as-full-screen"].includes(s) },
};
SnippetBoxDialog.defaultProps = {
    ...Dialog.defaultProps,
};

class SnippetBox extends Component {
    setup(){
        /** setup method */
        useSubEnv({'SnippetBox':this})
    }
}

SnippetBox.template = 'theme_alan.snippet_box';
SnippetBox.components = { SnippetBoxDialog, SnippetPicker };

class SnippetBoxBuilder extends Component {
    setup() {
        var self = this;
        /** setup method */

        // this.dialogs = useWowlService('dialog');
        this.props.size = "as-full-screen"

        onRendered(() => {
            self.call("dialog", "add", SnippetBox, self.props);
            // this.dialogs.add(, this.props);
        });
    }
}

SnippetBoxBuilder.template = xml``;

export default {
    SnippetBoxDialog:SnippetBoxDialog,
    SnippetBox: SnippetBox,
    SnippetBoxBuilder:SnippetBoxBuilder
}