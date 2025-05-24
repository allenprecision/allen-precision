/** @odoo-module alias=theme_alan.MegaMenuCategory **/

import { Dialog } from "@web/core/dialog/dialog";
import { alanTemplate } from "theme_alan.mixins";
import { useService } from "@web/core/utils/hooks";
import { SelectData } from "theme_alan.SelectData";

const { Component, useSubEnv, onMounted, useState } = owl;

class SubCategory extends Component {
    setup() {
        this.title = "Select Category";
        this.footer = false;
        this.header = true;
        this.search = "product.public.category"
        this.props.selected_cat = [];
        this.rpc = useService("rpc");
        onMounted(this._select2);
    }

    _select2(ev){
        let $input = $(this.__owl__.bdom.refs.modalRef).find("#as_sub_category_search")
        let self = this;
        $input.select2({
            width: "100%",
            tokenSeparators:[","],
            multiple: true,
            minimumInputLength: 2,
            maximumSelectionSize: 100,
            dropdownCssClass: 'as-select2-dropdown',
            allowClear: true,
            ajax: {
                url: "/select/data/fetch",
                quietMillis: 100,
                dataType: 'json',
                data: function (terms) {
                    return ({ terms:terms, searchIn:JSON.stringify([self.search]), parent_category:self.props.parent_id});
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
        // $input.select2('container').find('ul.select2-choices').sortable({
        //     containment: 'parent',
        //     update: function () { $input.select2('onSortEnd'); }
        // });
        $input.select2('container').find('ul.select2-choices');

        this._init_selection($input, this.props.pre_selected_vals)

    }
    async _init_selection($input, vals){
        if(vals != "" && vals != undefined){
            let type_ids = vals.split(",")
            let details = await this.rpc('/get_records_details',{'record_ids':type_ids, 'model':"product.public.category"});
            for (const cats of details) {
                this.props.selected_cat.push({'id':cats['id'],'text':cats['name']})
            }
        }
        $input.select2('data', this.props.selected_cat)
    }

    _procedureData(rec) {
        rec.forEach(ele => { ele['text'] = ele['name'] });
        return rec;
    }
    _selectionDone(ev){
        let $input = $(this.__owl__.bdom.refs.modalRef).find("#as_sub_category_search").val();
        // $(ev.target).attr("data-subcat",$input);
        this.props._submit_second_category($input);
        this.props.close();
    }
}

SubCategory.components = { Dialog };
SubCategory.template = "theme_alan.m_sub_category";


class MegaMenuCategory extends Component {
    setup(){
        /** Setup Method  */

        // Frame Columne Size
        this.props.col_size = this.env.SnippetBox.props.col_size;
        // Select Config Identifier
        this.props.selete_data_config = "MegaMenuCategory"
        // subcategory records init
        this.subCategory = useState({'second_level':[],'second_level_ids':[]});
        // dialog subcategory
        this.dialog = useService("dialog");
        this.rpc = useService("rpc");
        // Search
        this.props.search = "product.public.category";
        // Quick Search Option
        this.props.quick_search = ['top_level','asc_records','desc_records', 'random_records']

        // Slider Styles
        this.props.slider_styles = [['Slider Style 1','theme_alan.m_category_slider', 'as-mm-category-slider-1'],
        ['Slider Style 2','theme_alan.m_category_slider', 'as-mm-category-slider-2'],
        ['Slider Style 3','theme_alan.m_category_slider', 'as-mm-category-slider-3'],
        ['Slider Style 4','theme_alan.m_category_slider', 'as-mm-category-slider-4']]

        // Grid Styles
        this.props.grid_styles = [['Slider Style 1','theme_alan.m_category_grid', 'as-mm-category-grid-1'],
        ['Slider Style 2','theme_alan.m_category_grid', 'as-mm-category-grid-2'],
        ['Slider Style 3','theme_alan.m_category_grid', 'as-mm-category-grid-3'],
        ['Slider Style 4','theme_alan.m_category_grid', 'as-mm-category-grid-4'],
        ['Slider Style 5','theme_alan.m_category_grid', 'as-mm-category-grid-5']]

         // Design and Edit option

        if(this.env.SnippetBox.props.initData != undefined){
            this.props.design_and_edit = this.env.SnippetBox.props.initData.design_edit;
            this.props.init_record_ids = this.env.SnippetBox.props.initData.record_ids
            this.subCategory.second_level_ids = this.env.SnippetBox.props.initData.extra_info
        }else{
            this.props.design_and_edit = {
                'snippet':'MegaMenuCategory',
                'frame_col':this.props.col_size,
                'active_view':'slider',
                'auto_slider':true,
                'slider_time':4,
                'default_stemplate_id':'theme_alan.m_category_slider',
                'default_gtemplate_id':'theme_alan.m_category_grid',
                'template_id':'theme_alan.m_category_slider',
                'slider_style':'as-mm-category-slider-1',
                'grid_style':'as-mm-category-grid-1',
                'col_item':4,
                'slider':true,
                'grid':true,
            }
        }
        useSubEnv({"MegaMenuCategory":this})
    }
    _subCategory(id, ev, pre_select_cats){
        this.dialog.add(SubCategory, {
            parent_id:id,
            pre_selected_vals:pre_select_cats,
            pre_selected_data:this.subCategory.second_level,
            _submit_second_category: async(vals)=>{
                // Set category at button
                $(ev.target).attr("data-sub-cat",vals);
                // Here we get sub categpry and parent category
                if(vals != "" && vals!= undefined){
                    let type_ids = vals.split(",");
                    this._init_sub_cat_data(id, type_ids)
                }else{
                    this._init_sub_cat_data(id, [])
                }
            }
        });
    }
    async _init_sub_cat_data(parent_id, type_ids){

        let second_level = this.subCategory.second_level;
        let second_level_ids = this.subCategory.second_level_ids;

        let sl_info_update = false;
        let sl_ids_update = false;
        let details = [];
        if(type_ids != []){
            details = await this.rpc('/get_records_details',{'record_ids':type_ids, 'model':"product.public.category"});
        }
        for (const sl_info of second_level) {
            if(parent_id  == sl_info['parent']){
                sl_info['childs'] = details;
                sl_info_update = true;
            }
        }

        for (const sl_ids of second_level_ids) {
           if(sl_ids['parent'] == parent_id){
                sl_ids['childs'] = type_ids;
                sl_ids_update = true;
            }
        }

        if(!sl_info_update){
            second_level.push({'parent':parent_id,'childs':details});
        }
        if(!sl_ids_update){
            second_level_ids.push({'parent':parent_id,'childs':type_ids});
        }
    }

}

MegaMenuCategory.template = 'theme_alan.m_category_configuration';
MegaMenuCategory.components = { SelectData , SubCategory};


export default {
    MegaMenuCategory: MegaMenuCategory,
}