/** @odoo-module alias=theme_alan.FrameMaker **/

import { useService } from "@web/core/utils/hooks";

const { Component, useState, useSubEnv, onMounted, onWillStart } = owl;

class FrameOption extends Component {
    /** shows the frame option like custom and our default */
    _custom_frame(){
        this.env.SnippetBuilder.frameCustomTemplate = false;
        this.env.SnippetBuilder.PreviewframeTemplate = false;
        this.env.SnippetBuilder.defaultFrame = false;
        this.env.FrameMaker.state.frame_stage = "CustomFrame";
    }
    _default_frame(){
        this.env.FrameMaker.state.frame_stage = "DefaultFrame";
    }
}

FrameOption.template = "theme_alan.frame_option"

class CustomFrame extends Component {
    /** helps to create custom frame based on user need */

    controllers = useState({"frame_create":false})

    _active_frame_option(){
        this.env.FrameMaker.state.frame_stage = "FrameOption";
    }
    _frame_done(){
        /** Action on submit the frame */
        let $modal = $(this.__owl__.bdom.parentEl);
        $modal.find(".as-grid-active").removeClass("as-grid-active");
        this.env.SnippetBuilder.frameCustomTemplate = $modal.find(".as-frame-work");
        this.env.SnippetBuilder.PreviewframeTemplate = false;
        this.env.SnippetBuilder.defaultFrame = false;
        this.env.SnippetBuilder.state.active_component = "FrameData";
    }
    _update_frame_grid(init_stage=true){
        /** Make frame based on rows and cols */
        let $modal = $(this.__owl__.bdom.parentEl);
        var row = $modal.find("#as-row").val();
        var column = $modal.find("#as-column").val();
        if(row == '0' || column == '0'){
            this.controllers.frame_create = false;
        }
        if(row != '0' && column != '0'){
            this.controllers.frame_create = true;
            if(init_stage){
                let frame_template = "";
                for (let r = 0; r < row; r++) {
                    let col_template = "";
                    
                    let col_val = 12 / column;
                    for (let c = 0; c < column; c++) {
                        let pos_id = "" + c + r;
                        let template = "<div class='col-lg-"+col_val+" as-grid as-min-height as-ghost-grid' \
                                        data-size='"+col_val+"' data-pos-id='"+ pos_id +"' data-row-id='"+ r +"'></div>";
                        col_template = col_template + template;
                    }
                    let row_template = "<div class='row' data-col-size='"+ col_val +"' data-id='"+r+"'>"+ col_template +"</div>";
                    frame_template = frame_template + row_template;
                }
                $(this.__owl__.bdom.parentEl).find(".as-frame-work").empty().append(frame_template);
            }
            this._update_frame_grid_merge($modal, init_stage);
        }
    }
    _update_frame_grid_merge($model, init_stage=true){
        /** Do frame merge */

        var self = this;
        $model.find(".as-grid").click(function(ev){
            let $click_box = $(ev.currentTarget);
            let $parent = $(ev.currentTarget).parent();
            let $active_box = $model.find(".as-grid-active");
            if($click_box.hasClass("as-grid-active")){
                if($click_box.prev().hasClass("as-grid-active") && $click_box.next().hasClass("as-grid-active")){
                    $active_box.removeClass("as-grid-active");
                }else{
                    if(!init_stage){
                        $click_box.addClass("as-grid-active");
                    }else{
                        $click_box.removeClass("as-grid-active");
                    }
                }
            }else{
                let parent_id = $parent.data('id');
                var incorrect_point = 0;
                for (let e = 0; e < $active_box.length; e++) {
                    let cur_par_id = $($active_box[e]).parent().data('id');
                    if(cur_par_id != parent_id){
                        incorrect_point++;
                        break;
                    }
                }
                if(incorrect_point){
                    $active_box.removeClass("as-grid-active");
                    $click_box.addClass("as-grid-active");
                }else{
                    if($click_box.prev().hasClass("as-grid-active") || $click_box.next().hasClass("as-grid-active")){
                        $click_box.addClass("as-grid-active");
                    }else{
                        $active_box.removeClass("as-grid-active");
                        $click_box.addClass("as-grid-active");
                    }
                }
            }
        })
        $model.find(".as-frame-merge").click(function (ev) {
            let $frame = $model.find(".as-frame-work");
            let $merge = $frame.find(".as-grid-active");
            if($merge.length > 1){
                let $first_div = $merge[0];
                let default_size = $($first_div).parent().data('colSize');
                let row_id = $($first_div).parent().data('id');
                let size = 0;
                for (let e = 0; e < $merge.length; e++) {
                    size = size + $($merge[e]).data('size');
                }
                let pos_id = "" + row_id + size;
                if(default_size != size){
                    var template = "<div class='col-lg-"+size+" as-grid as-min-height as-rest-grid as-ghost-grid' data-size='"+size+"' \
                                    data-pos-id='"+ pos_id +"' data-row-id='"+ row_id +"'/>";
                }else{
                    var template = "<div class='col-lg-"+size+" as-grid as-min-height as-ghost-grid' data-size='"+size+"' \
                                    data-pos-id='"+ pos_id +"' data-row-id='"+ row_id +"'/>";
                }

                $(template).insertBefore($first_div);
                $merge.remove();
                self._update_frame_grid(false);
            }
        })
        $model.find(".as-frame-reset").click(function (ev) {
            let $frame = $model.find(".as-frame-work");
            let $merge = $frame.find(".as-grid-active");

            if($merge.length == 1){
                let $first_div = $merge[0];
                let default_size = $($first_div).parent().data('colSize')
                let row_id = $($first_div).parent().data('id');
                let size = $($merge[0]).data('size') / $($first_div).parent().data('colSize');
                let template = "";
                for (let i = 0; i < size; i++) {
                    let pos_id = "" + row_id + i;
                    template = template + "<div class='col-lg-"+default_size+" as-grid as-min-height as-ghost-grid' data-size='"+default_size+"' \
                                data-pos-id='"+ pos_id +"' data-row-id='"+ row_id +"'/>";
                }
                $(template).insertAfter($first_div);
                $first_div.remove();
                self._update_frame_grid(false);
            }
        })
    }
}

CustomFrame.template = "theme_alan.custom_frame"

class DefaultFrame extends Component {
    /** shows all the alan default and custom frame */

    setup(){
        this.rpc = useService("rpc");
        onWillStart(async()=>{
            this.data = await this.rpc('/get_default_frame');
        })
        onMounted(()=>{
            $(this.__owl__.bdom.parentEl).find("#as_default_frame").empty().html(this.data.response)
            $(this.__owl__.bdom.parentEl).find(".as_frame").click((ev)=>{
                this._select_frame(ev);
            })
            $(this.__owl__.bdom.parentEl).find(".as_delete_frame").click((ev)=>{
                this._delete_frame(ev);
            })
        })
    }

    _active_frame_option(){
        this.env.FrameMaker.state.frame_stage = "FrameOption";
    }
    async _delete_frame(ev){
        let frame_id = $(ev.currentTarget).attr('data-frame_id');
        $(ev.currentTarget).parents('.as-frame-temp').remove();
        return await this.rpc('/delete_default_frame',{'frame_id':frame_id});
    }
    async _select_frame(ev){
        let frame =  await this.rpc('/get_frame',{'frame_id':$(ev.currentTarget).attr('data-frame_id')});
        this.env.SnippetBuilder.frameCustomTemplate = $("<div>"+frame+"</div>");
        this.env.SnippetBuilder.PreviewframeTemplate = false;
        this.env.SnippetBuilder.defaultFrame = true;
        this.env.SnippetBuilder.defaultFrameId = $(ev.currentTarget).attr('data-frame_id');
        this.env.SnippetBuilder.state.active_component = "FrameData";
    }
}

DefaultFrame.template = "theme_alan.default_frame"

class FrameMaker extends Component {
    /** Main component for the creation of framemaker */

    state = useState({ frame_stage: "FrameOption"});

    setup(){
        useSubEnv({'FrameMaker': this})
        this.env.SnippetBuilder.frameCustomTemplate = false;
    }

    get activeFrameComponent() {
        /** frame component activator  */
        const stage = this.state.frame_stage;
        if(stage == "FrameOption"){ return FrameOption }
        else if(stage == "CustomFrame"){ return CustomFrame }
        else if(stage == "DefaultFrame"){ return DefaultFrame }
    }
}

FrameMaker.template = 'theme_alan.frame_maker';
FrameMaker.components = { FrameOption, CustomFrame, DefaultFrame };

export default {
    FrameMaker: FrameMaker,
}