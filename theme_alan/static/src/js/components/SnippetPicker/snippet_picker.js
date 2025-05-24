/** @odoo-module alias=theme_alan.SnippetPicker **/

import { MegaMenuProduct } from "theme_alan.MegaMenuProduct";
import { MegaMenuCategory } from "theme_alan.MegaMenuCategory";
import { MegaMenuBrand } from "theme_alan.MegaMenuBrand";
import { MegaMenuContent } from "theme_alan.MegaMenuContent";
import { ProductSlider } from "theme_alan.ProductSlider";
import { BestSellingProduct } from "theme_alan.BestSellingProduct";
import { LatestProduct } from "theme_alan.LatestProduct";
import { BrandProduct } from "theme_alan.BrandProduct";
import { CategoryProduct } from "theme_alan.CategoryProduct";
import { ProductBanner } from "theme_alan.ProductBanner";
import { CategorySlider } from "theme_alan.CategorySlider";
import { BrandSlider } from "theme_alan.BrandSlider";
import { BlogSlider } from "theme_alan.BlogSlider";
import { StaticSnippet } from "theme_alan.StaticSnippet";

const { Component, useState, useSubEnv } = owl;

class SnippetList extends Component {
    setup(){
        /** Setup Method */
        this.snippet_list = this.env.SnippetBox.props.snippet_list;
    }
    _select_snippet(ev){
        /** Select Snippet */
        let snippetConfig = $(ev.target).parents(".as_snippet").attr("data-snippet-name");
        if(snippetConfig != undefined){
            this.env.SnippetPicker.state.active_snippet = snippetConfig;
        }
    }
    _back_to_frame(){
        this.env.SnippetBox.props.close();
    }
}

SnippetList.template = 'theme_alan.snippet_list';
SnippetList.components = { };

class SnippetPicker extends Component {
    setup(){
        /** Setup Method */
        useSubEnv({'SnippetPicker':this});
        let initSnippet = this.env.SnippetBox.props.initSnippet;

        this.init_snippet = initSnippet != undefined ? initSnippet: "SnippetList";
        this.state = useState({ active_snippet: this.init_snippet });
    }

    get activeSnippet() {
        /** Snippet Activation Method */
        const stage = this.state.active_snippet;
        if(stage == "SnippetList"){ return SnippetList }
        else if(stage == "MegaMenuProduct"){ return MegaMenuProduct }
        else if(stage == "MegaMenuCategory"){ return MegaMenuCategory }
        else if(stage == "MegaMenuBrand"){ return MegaMenuBrand }
        else if(stage == "MegaMenuContent"){ return MegaMenuContent }
        else if(stage == "ProductSlider"){ return ProductSlider }
        else if(stage == "BestSellingProduct"){ return BestSellingProduct }
        else if(stage == "LatestProduct"){ return LatestProduct }
        else if(stage == "BrandProduct"){ return BrandProduct }
        else if(stage == "CategoryProduct"){ return CategoryProduct }
        else if(stage == "ProductBanner"){ return ProductBanner }
        else if(stage == "CategorySlider"){ return CategorySlider }
        else if(stage == "BrandSlider"){ return BrandSlider }
        else if(stage == "BlogSlider"){ return BlogSlider }
        else if(stage == "StaticSnippet"){ return StaticSnippet }

    }
}

SnippetPicker.template = 'theme_alan.snippet_picker';
SnippetPicker.components = { SnippetList,
    MegaMenuCategory, MegaMenuProduct, MegaMenuBrand, MegaMenuContent,
    ProductSlider, BestSellingProduct, LatestProduct, BrandProduct, CategoryProduct,
    ProductBanner, CategorySlider, BrandSlider, BlogSlider, StaticSnippet };

export default {
    SnippetPicker: SnippetPicker,
}
