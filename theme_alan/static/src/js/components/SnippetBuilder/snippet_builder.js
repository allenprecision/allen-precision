/** @odoo-module alias=theme_alan.SnippetBuilder **/

import { useService } from "@web/core/utils/hooks";
// import { useWowlService } from '@web/legacy/utils';
import { Dialog } from "@web/core/dialog/dialog";
import { FrameMaker } from "theme_alan.FrameMaker";
import { FrameData } from "theme_alan.FrameData";
import { FramePreview } from "theme_alan.FramePreview";

const { Component, useState, onRendered, xml, useSubEnv, onWillStart } = owl;

class FrameDialog extends Dialog {}
FrameDialog.props = {
    ...Dialog.props,
    size: { type: String, optional: true, validate: (s) => ["sm", "md", "lg", "xl" ,"as-full-screen"].includes(s) },
};
FrameDialog.defaultProps = {
    ...Dialog.defaultProps,
};

class SnippetBuilder extends Component {

    setup() {
        /** setup method */
        this.rpc = useService("rpc");
        useSubEnv({'SnippetBuilder':this});
        onWillStart(this.initlized);
        this.state = useState({ active_component: this._get_state() });
    }
    async initlized(){
        this._getPreviewframeTemplate(true)
    }
    _get_state(){
        let frame_config = this.props.snippet_origin.$target.attr('data-frame-work');
        let frame_id = this.props.snippet_origin.$target.attr('data-frame-id');
        if( frame_config != undefined && frame_id  != undefined ){
            return "FramePreview";
        }else{
            return "FrameMaker";
        }
    }
    async _getPreviewframeTemplate(init){
        let frame_config = this.props.snippet_origin.$target.attr('data-frame-work');
        let frame_id = this.props.snippet_origin.$target.attr('data-frame-id');
        if( frame_config != undefined && frame_id  != undefined ){
            let data = await this.rpc('/get_snippet_frame',{'frame_id':frame_id,'frame_config':frame_config})
            if(init){
                if(data.frame_id != false && data.frame_config != false){
                    this.frameCustomTemplate = $(data.frame_id);
                    this.PreviewframeTemplate = $(data.frame_config);
                    this.state.active_component = "FramePreview";
                    this.defaultFrame = true;
                    this.defaultFrameId = this.props.snippet_origin.$target.attr('data-frame-id');
                }else{
                    this.frameCustomTemplate = false;
                    this.PreviewframeTemplate = false;
                }
            }else{
                if(data.frame_id != false && data.frame_config != false){
                    if(this.PreviewframeTemplate != false && this.PreviewframeTemplate != undefined){
                        return this.PreviewframeTemplate
                    }else{
                        return $(data.frame_config);
                    }
                }else{
                    return this.PreviewframeTemplate
                }
            }
        }else{
            if(this.PreviewframeTemplate){
                return this.PreviewframeTemplate
            }else{
                this.frameCustomTemplate = false;
                this.PreviewframeTemplate = false;
            }
        }
    }

    get activeComponent() {
        /** active the component based on state */
        const stage = this.state.active_component;
        if(stage == "FrameMaker"){ return FrameMaker }
        else if(stage == "FrameData"){ return FrameData }
        else if(stage == "FramePreview"){ return FramePreview }
    }
}

SnippetBuilder.template = 'theme_alan.snippetBuilder';
// this are the core components of frame maker...
SnippetBuilder.components = { FrameDialog, FrameMaker, FrameData, FramePreview };

class SnippetBuilderWrapper extends Component {
    setup() {
        /** setup method */

        this.dialog = useService("dialog");
        this.props.size = "as-full-screen"

        // onRendered(() => {
        this.dialog.add(SnippetBuilder, this.props);
        // });
    }
}
SnippetBuilderWrapper.template = xml``;

export default {
    SnippetBuilder: SnippetBuilder,
    SnippetBuilderWrapper: SnippetBuilderWrapper,
}
