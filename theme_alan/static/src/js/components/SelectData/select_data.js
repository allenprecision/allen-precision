/** @odoo-module alias=theme_alan.SelectData **/

import { alanTemplate } from "theme_alan.mixins";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { UserInformDialog } from 'theme_alan.UserInformDialog';
const { Component, useState, onMounted, useRef} = owl;

class SelectData extends Component {
    setup() {

        // Initlized data of snippets....
        this.dialog = useService("dialog");
        this.state = useState({'record_info':[], 'record_ids':[]})
        this.rpc = useService("rpc");
        this.call = useRef("call");
        this.design_editor = useState(this.props.design_and_edit);
        this.bindedSortable = [];

        if(this.props.init_record_ids != undefined){
            this._init_records(this.props.init_record_ids)
        }
        onMounted(this._select2);
        if(this.props.only_preview){
            this._open_preview()
        }
    }
    async _init_records(record_ids){
        this.state.record_ids = record_ids;
        let details = await this.rpc('/get_records_details',{'record_ids':record_ids, 'model':this.props.search})
        this.state.record_info = details;
    }
    _sortable(){
        let dataGroupId;
        var data = $(this.__owl__.bdom.el).find(".as-sortable-record").sortable({
            placeholder:"<li class='ui-sortable-placeholder'></li>",
            onDragStart: (params) => {
                params[0].classList.add('drag-start')
                dataGroupId = 1;
            },
            onDrop: (params) => {
                params[0].classList.remove('drag-start')
                this._update_record_sequence(dataGroupId, params)
            },
        });
    }

    async _update_record_sequence(dataGroupId, params){
        let sort_record = $(this.__owl__.bdom.parentEl).find(".as_data_info");
        let sort_record_list = [];
        for (const ele of sort_record) {
            sort_record_list.push($(ele).data("id"));
        }
        this.state.record_ids = sort_record_list;
    }
    _select2(){
        // Use to select the records....

        let $input = $(this.__owl__.bdom.el).find("#as_search");
        let self = this;

        $input.select2({
            width: "100%",
            tokenSeparators:[","],
            minimumInputLength: 2,
            placeholder:_t("Search Items ...."),
            multiple: false,
            maximumSelectionSize: 100,
            dropdownCssClass: 'as-select2-dropdown',
            allowClear: true,
            initSelection: function (ele, cbf) { },
            ajax: {
                url: "/select/data/fetch",
                quietMillis: 100,
                dataType: 'json',
                data: function (terms) {
                    return ({ terms:terms, searchIn:JSON.stringify([self.props.search])});
                },
                results: function (rec) {
                    return {
                        results: self._procedureData(rec)
                    };
                },
            },
            formatResult: function (res) {
                return alanTemplate.getStaticTemplate("theme_alan.select2_fetch_info",res);
            },
        });
        this._onSelect();
        this._sortable();

    }
    _procedureData(rec) {
        rec.forEach(ele => { ele['text'] = ele['name'] });
        return rec;
    }
    _delete(ev){
        // Use to delete records....
        let rec_id = $(ev.target).parents(".as_data_info").attr("data-id");
        for (var i = 0; i < this.state.record_ids.length; i++) {
            if (this.state.record_ids[i] == rec_id) {
                this.state.record_ids.splice(i, 1);
            }
            if(this.state.record_info[i]['id'] == rec_id){
                this.state.record_info.splice(i, 1);
            }
        }
        $(ev.target).parents(".as_data_info").remove();
    }
    _onSelect(){
        // Use to update the record list....
        let $input = $(this.__owl__.bdom.el).find("#as_search");
        $input.on("select2-selecting", async (ev)=> {
            if(this.state.record_ids.indexOf(ev.val) == -1){
                let details = await this.rpc('/get_record_detail',{
                    'record_id':ev.val,
                    'model':this.props.search,
                    'exists_data':this.state.record_info })
                this.state.record_ids.push(ev.val);
                this.state.record_info.push(details);
            }
        });
    }
    async _get_latest_product(){
        let details = await this.rpc('/get_quick_record',{'mode':'get_latest_product'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_top_product(){
        let details = await this.rpc('/get_quick_record',{'mode':'get_top_product'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_best_sold_product(){
        let details = await this.rpc('/get_quick_record',{'mode':'get_best_sold_product'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_random_product(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_random_product'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_parent_category(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_parent_category'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_a_to_z_category(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_a_to_z_category'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_z_to_a_category(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_z_to_a_category'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_random_category(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_random_category'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_random_brand(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_random_brand'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_a_to_z_brand(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_a_to_z_brand'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_z_to_a_brand(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_z_to_a_brand'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_random_blog(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_random_blog'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_a_to_z_blog(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_a_to_z_blog'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    async _get_z_to_a_blog(){
        let details = await this.rpc('/get_quick_record',{'mode':'_get_z_to_a_blog'})
        if(details.length != 0){
            this._assign_data(details)
        }
    }
    _assign_data(data){
        // Use to assign the pre get record ....
        for (var i = 0; i < data.length; i++) {
            if(this.state.record_ids.indexOf(data[i]['id']) == -1){
                this.state.record_ids.push(data[i]['id']);
                this.state.record_info.push({'id':data[i]['id'],'display_name':data[i]['display_name'],'image':data[i]['image']})
            }
        }
        this._sortable();
    }
    _change_active_view(ev){

        let megamenu_snippet_lst = ['MegaMenuCategory','MegaMenuProduct', 'MegaMenuBrand']
        let product_snippet_lst = ['ProductSlider','BestSellingProduct', 'LatestProduct', 'BrandProduct', 'CategoryProduct', 'ProductBanner', 'CategorySlider', 'BrandSlider', 'BlogSlider']

        if(megamenu_snippet_lst.includes(this.props.selete_data_config)){
            this.design_editor.active_view = $(ev.target).val();
        }else if(product_snippet_lst.includes(this.props.selete_data_config)){
            this.design_editor.view = $(ev.target).val();
        }

        if($(ev.target).val() == "grid"){
            this.design_editor.auto_slider = false;
            this.design_editor.template_id = this.design_editor.default_gtemplate_id
        }else{
            this.design_editor.template_id = this.design_editor.default_stemplate_id
        }

        this._get_preview();
    }
    _change_auto_slider(ev){
        if(this.design_editor.auto_slider){
            this.design_editor.auto_slider = false;
        }else{
            this.design_editor.auto_slider = true;
        }
        this._get_preview();
    }
    _change_slider_time(ev){
        this.design_editor.slider_time = $(ev.target).val();
        this._get_preview();
    }
    _change_col_item(ev){
        let megamenu_snippet_lst = ['MegaMenuCategory','MegaMenuProduct', 'MegaMenuBrand']
        let product_snippet_lst = ['ProductSlider','BestSellingProduct', 'LatestProduct', 'BrandProduct', 'CategoryProduct', 'ProductBanner', 'CategorySlider', 'BrandSlider', 'BlogSlider']

        if(megamenu_snippet_lst.includes(this.props.selete_data_config)){
            this.design_editor.col_item = $(ev.target).val();
        }
        else if(product_snippet_lst.includes(this.props.selete_data_config)){
            let screen_view = $(ev.target).attr("data-view-type")
            if(screen_view == "desk"){
                this.design_editor.default_col_desk = $(ev.target).val();
            }else if(screen_view == "mob"){
                this.design_editor.default_col_mob = $(ev.target).val();
            }
            // this.design_editor.view = $(ev.target).val();
        }

        this._get_preview();
    }
    _change_grid_style(ev){
        this.design_editor.grid_style = $(ev.target).val();
        let option = "[value='"+ $(ev.target).val() +"']";
        this.design_editor.template_id = $(ev.target).find(option).attr("data-template");
        this._get_preview();
    }
    _change_slider_style(ev){
        this.design_editor.slider_style = $(ev.target).val();
        let option = "[value='"+ $(ev.target).val() +"']";
        this.design_editor.template_id = $(ev.target).find(option).attr("data-template");
        this._get_preview();
    }
    _change_pagination(ev){
        this.design_editor.pagination = $(ev.target).val();
        this._get_preview();
    }
    _change_quick_option(ev){
        let quick_option = $(ev.target).data("target");

        if(quick_option == "allow_add_to_cart"){
            this.design_editor.allow_add_to_cart = $(ev.target).prop("checked");
        }else if(quick_option == "allow_quick_view"){
            this.design_editor.allow_quick_view = $(ev.target).prop("checked");
        }else if(quick_option == "allow_compare"){
            this.design_editor.allow_compare = $(ev.target).prop("checked");
        }else if(quick_option == "allow_wishlist"){
            this.design_editor.allow_wishlist = $(ev.target).prop("checked");
        }else if(quick_option == "allow_rating"){
            this.design_editor.allow_rating = $(ev.target).prop("checked");
        }else if(quick_option == "allow_label"){
            this.design_editor.allow_label = $(ev.target).prop("checked");
        }else if(quick_option == "allow_hover_image"){
            this.design_editor.allow_hover_image = $(ev.target).prop("checked");
        }else if(quick_option == "allow_stock_info"){
            this.design_editor.allow_stock_info = $(ev.target).prop("checked");
        }else if(quick_option == "allow_offer_time"){
            this.design_editor.allow_offer_time = $(ev.target).prop("checked");
        }else if(quick_option == "allow_brand_info"){
            this.design_editor.allow_brand_info = $(ev.target).prop("checked");
        }else if(quick_option == "allow_color_variant"){
            this.design_editor.allow_color_variant = $(ev.target).prop("checked");
        }else if(quick_option == "loop"){
            this.design_editor.loop = $(ev.target).prop("checked");
        }else if(quick_option == "tabs"){
            this.design_editor.tabs = $(ev.target).prop("checked");
        }else if(quick_option == "allow_link"){
            this.design_editor.allow_link = $(ev.target).prop("checked");
        }
        this._get_preview();
    }
    async _get_preview(){
        //  Use to show the preview of snippets
        let megamenu_preview = ['MegaMenuCategory','MegaMenuProduct', 'MegaMenuBrand'];
        let products_preview = ['ProductSlider','BestSellingProduct', 'LatestProduct', 'BrandProduct', 'CategoryProduct', 'ProductBanner', 'CategorySlider', 'BrandSlider','BlogSlider'];

        if(megamenu_preview.includes(this.props.selete_data_config)){
            let context = {
                'snippet':this.props.selete_data_config,
                'record_ids':this.state.record_ids,
                'modal':this.props.search,
                'design_editor':this.design_editor,
            }
            if(this.props.selete_data_config == "MegaMenuCategory" || this.props.selete_data_config == "MegaMenuCategory"){
                context['extra_info'] = this.props.extra_info.second_level_ids
            }
            let data = await this.rpc('/get_mega_snippet_template', context);
            $(this.__owl__.bdom.parentEl).find("#as_snippet_preview").empty().append(data.template)
            if(this.design_editor.active_view == 'slider'){
                new Swiper(".as_swiper", data.slider_config)
            }
        }else if(products_preview.includes(this.props.selete_data_config)){
            let records = {
                'snippet':this.props.selete_data_config,
                'record_ids':this.state.record_ids,
                'modal':this.props.search,
                'design_editor':this.design_editor
            }
            let data = await this.rpc('/get_products_snippet_template', records);
            $(this.__owl__.bdom.parentEl).find("#as_snippet_preview").empty().append(data.template)
            if(this.design_editor.view == 'slider'){
                new Swiper(".as_page_swiper", data.slider_config)
            }
        }

    }
    _open_preview(){
        this._get_preview();
    }
    _back_to_frame(){
        this.env.SnippetBox.props.close();
    }
    _save_snippet(){
        if(!this.state.record_ids.length){
            this.dialog = this.call("dialog", "add", UserInformDialog, {
                warning_msg:_t('Oops, Please configure a snippet before save.'),
                inform_type:"no_snippet_config",
                onConfirm: () => {
                    this.env.SnippetBuilder.state.active_component = "FrameMaker";
                },
            });

        }else{
            let snippet_origin = this.env.SnippetBox.props.snippet_origin
            snippet_origin.attr("data-snippet-name", this.design_editor.snippet)
            snippet_origin.attr("data-records-ids",JSON.stringify(this.state.record_ids))
            snippet_origin.attr("data-modal", this.props.search)
            snippet_origin.attr("data-design-edit", JSON.stringify(this.design_editor))
            if(this.design_editor.snippet == "MegaMenuCategory"){
                snippet_origin.attr("data-extra-info", JSON.stringify(this.props.extra_info.second_level_ids))
            }

            let btn = "<button class='btn as-e-btn-success as-snippet-btn m-2'><i class='fa fa-edit'></i> Edit </button> \
                    <button class='btn as-e-btn-danger as-snippet-rm-btn m-2'> <i class='fa fa-trash'></i> Remove </button>";

            $(snippet_origin).empty().append(btn);
            $(snippet_origin).find(".as-snippet-btn").click((ev)=>{
                ev.stopPropagation();
                this._openSnippet(ev, this.design_editor.snippet);
            });
            $(snippet_origin).find(".as-snippet-rm-btn").click((ev)=>{
                ev.stopPropagation();
                this._removeSnippet(ev);
            });
            this.env.SnippetBox.props.close();
        }
    }
    _openSnippet(ev, Snippet){
        if(Snippet != "SnippetList"){
            var initData = {
                'record_ids': JSON.parse($(ev.currentTarget).parent().attr("data-records-ids")),
                'modal': $(ev.currentTarget).parent().attr("data-modal"),
                'design_edit': JSON.parse($(ev.currentTarget).parent().attr("data-design-edit")),
            }
            if(Snippet == "MegaMenuCategory"){
                if($(ev.currentTarget).parent().attr("data-extra-info")){
                    initData['extra_info'] = JSON.parse($(ev.currentTarget).parent().attr("data-extra-info"))
                }
            }
        }
        const dialog = this.env.SnippetBox.props.SnippetBuilder.props.snippet_origin.call("dialog", "add", this.env.SnippetBox.props.SnippetBoxBuilder,{
            'title': 'Snippet Box',
            'initSnippet':Snippet,
            'initData':initData,
            'snippet_origin':$(ev.currentTarget).parent(),
            'SnippetBuilder':this.env.SnippetBox.props.SnippetBuilder,
            'SnippetBoxBuilder':this.env.SnippetBox.props.SnippetBoxBuilder,
            'snippet_list':this.env.SnippetBox.props.SnippetBuilder.props.snippet_list.snippets,
        });
        // dialog.mount(this.env.SnippetBox.props.SnippetBuilder.props.snippet_origin.el);
    }
    _removeSnippet(ev){
        var self = this;
        $(ev.currentTarget).parent().removeAttr("data-modal")
                            .removeAttr("data-snippet-name")
                            .removeAttr("data-records-ids")
                            .removeAttr("data-design-edit")
                            .removeAttr("data-extra-info")
                            .removeAttr("data-selected-templ-id")
                            .removeAttr("data-active-id")
        let btn = '<button class="btn as-e-btn-primary as-data-btn"><i class="fa fa-plus"></i> Add </button>';
        $(this.env.SnippetBox.props.snippet_origin).empty().append(btn)
        $(this.env.SnippetBox.props.snippet_origin).find(".as-data-btn").click((ev)=>{
            ev.stopPropagation();
            self._openSnippet(ev,'SnippetList');
        });
    }

    select_sub_category(ev){
        // Use to select the subcateory for megamenu
        let id = $(ev.target).data("id");
        let pre_select_cats = $(ev.target).attr("data-sub-cat");
        this.env.MegaMenuCategory._subCategory(id, ev, pre_select_cats);
    }

    get_sub_category(parent_id){
        // init sub catgeory at records
        for (const cat of this.props.extra_info.second_level_ids) {
            if(cat['parent'] == parent_id){
                return [cat['childs'].toString(), cat['childs'].length]
            }
        }
        return ["",0]
    }
}

SelectData.template = 'theme_alan.select_data_configure';

export default {
    SelectData: SelectData,
}