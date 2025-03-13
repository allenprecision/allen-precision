/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import VariantMixin from "@website_sale/js/variant_mixin";
import wSaleUtils from "@website_sale/js/website_sale_utils";
const cartHandlerMixin = wSaleUtils.cartHandlerMixin;

publicWidget.registry.MegaMenuTabsSnippets = publicWidget.Widget.extend({
    selector: '.as-mm-tabs-level-1',
    disabledInEditableMode:false,
    events:{
        'mouseenter':'_showMegaMenuTabs',
        'click .as-mob-tab-menu':'_showMegaMenuTabsMob',
    },
    _showMegaMenuTabs:function(ev){
        if($(ev.currentTarget).hasClass("active") == false){
            this.$target.parents(".as-mm-tabs-levels").find(".as-mm-tabs-level-1.active").removeClass("active");
            $(ev.currentTarget).addClass("active");
        }
    },
    _showMegaMenuTabsMob:function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        if($(ev.currentTarget).parents(".as-mm-tabs-level-1").hasClass("as-mob-menu")){
            $(ev.currentTarget).parents(".as-mm-tabs-level-1").removeClass("active").removeClass("as-mob-menu");
        }else{
            $(ev.currentTarget).parents(".as-mm-tabs-level-1").addClass("active").addClass("as-mob-menu");
        }
    }
});

publicWidget.registry.AdvanceMegaMenu = publicWidget.Widget.extend({
    selector: '.as-advance-header',
    start:function(){
        this.$target.find('.as-ah-mobile_menu').click(function (ev) {
            ev.stopPropagation();
            // $(ev.currentTarget).addClass("as-ah-h1-close")
            $(ev.currentTarget).parents(".as-l1-items").addClass("as-ah-h1-open").trigger('click');
        });
        this.$target.find('.as-ah-mobile_menu-l2').click(function (ev) {
            ev.stopPropagation();
            $(ev.currentTarget).parents(".as-l2-items").addClass("as-ah-h2-open").trigger('click');
        });
        this.$target.find('.as-ah-mobile_menu-l3').click(function (ev) {
            ev.stopPropagation();
            $(ev.currentTarget).parents(".as-l3-items").addClass("as-ah-h3-open").trigger('click');
        });
    },
});

publicWidget.registry.AdvanceMegaMenuMobile = publicWidget.Widget.extend({
    selector: '.as-mob-2nd-menu',
    start:function(){
        this.$target.find('.as_mob_2nd_btn').click(function(ev){
            $($(ev.currentTarget)[0].nextElementSibling).addClass("as-advance-header-open")
        })
        this.$target.find('.as-bbl-1').click(function(ev){
            $(ev.currentTarget).parents(".as-advance-header").removeClass("as-advance-header-open")
        })
        this.$target.find('.as-bbl-2').click(function(ev){
            $(ev.currentTarget).parents(".as-l1-items").removeClass("as-ah-h1-open")
        })
        this.$target.find('.as-bbl-3').click(function(ev){
            $(ev.currentTarget).parents(".as-l2-items").removeClass("as-ah-h2-open")
        })
        this.$target.find('.as-bbl-4').click(function(ev){
            $(ev.currentTarget).parents(".as-l3-items").removeClass("as-ah-h3-open")
        })
    }
});

publicWidget.registry.MegaMenuSnippets = publicWidget.Widget.extend({
    selector: '.nav-item',
    disabledInEditableMode:false,
    is_clicked :false,
    events:{
        'click .as-advance-nav-mob':'_advanceNavMob',
        'click .as-advance-header-close':'_advanceNavMobClose',
        'click':'_showMegaMenu',
        'click .swiper-button-next, .swiper-button-prev':'_stopCloseMenu',
        'mouseenter':'_showMegaMenu',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },
    _stopCloseMenu:function(ev){
        ev.preventDefault();
        ev.stopPropagation()
    },
    start:function(){
        this.$target.find('.as-ah-mobile_menu-l1').click(function (ev) {
            $(ev.currentTarget).click(function (ev) {
                if($(ev.currentTarget).parents(".as-ah-h1-open").length){
                    $(ev.currentTarget).parents(".as-l1-items").removeClass("as-ah-h1-open");
                    $($(ev.currentTarget)[0].nextElementSibling).find(".as-l2-items").removeClass("as-ah-h2-open")
                    $($(ev.currentTarget)[0].nextElementSibling).find(".as-l3-items").removeClass("as-ah-h3-open")
                }
                else{
                    $(ev.currentTarget).parents(".as-l1-items").addClass("as-ah-h1-open").trigger('click');
                }
            });

        });
        this.$target.find('.as-ah-mobile_menu-l2').click(function (ev) {
            $(ev.currentTarget).click(function (ev) {
                if($(ev.currentTarget).parents(".as-ah-h2-open").length){
                    $(ev.currentTarget).parents(".as-l2-items").removeClass("as-ah-h2-open");
                    $($(ev.currentTarget).parents(".as-l2-link")[0].nextElementSibling).find(".as-l3-items").removeClass("as-ah-h3-open")
                }
                else{
                    $(ev.currentTarget).parents(".as-l2-items").addClass("as-ah-h2-open").trigger('click');
                }
            });

        });
        this.$target.find('.as-ah-mobile_menu-l3').click(function (ev) {
            $(ev.currentTarget).click(function (ev) {
                if($(ev.currentTarget).parents(".as-ah-h3-open").length){
                    $(ev.currentTarget).parents(".as-l3-items").removeClass("as-ah-h3-open");
                }
                else{
                    $(ev.currentTarget).parents(".as-l3-items").addClass("as-ah-h3-open").trigger('click');
                }
            });
        });
    },
    _advanceNavMob: function(ev){
        $($(ev.currentTarget)).addClass("as-advance-header-close")
        $($(ev.currentTarget)[0].nextElementSibling).addClass("as-advance-header-open")

    },
    _advanceNavMobClose:function(ev){
        $($(ev.currentTarget)).removeClass("as-advance-header-close")
        $($(ev.currentTarget)[0].nextElementSibling).removeClass("as-advance-header-open")
        $($(ev.currentTarget)[0].nextElementSibling).find(".as-l1-items").removeClass("as-ah-h1-open")
        $($(ev.currentTarget)[0].nextElementSibling).find(".as-l2-items").removeClass("as-ah-h2-open")
        $($(ev.currentTarget)[0].nextElementSibling).find(".as-l3-items").removeClass("as-ah-h3-open")
    },
    _showMegaMenu: async function(ev){
        var breakpoint = window.matchMedia('(max-width:767px)');
        if((!this.is_clicked && !this.editableMode) || breakpoint['matches'] == true ){
            let loader = '<div class="spinner-border" role="status"> <span class="visually-hidden">Loading...</span></div>'
            let snippetList = this.$target.find('[data-snippet-name]:not([data-snippet-name="MegaMenuContent"])').empty().append(loader);
            for (const snippet of snippetList) {
                let static_snippet = ['MegaMenuContent'];
                if(!static_snippet.includes($(snippet).attr("data-snippet-name"))){
                    let context = {
                        'snippet':$(snippet).attr("data-snippet-name"),
                        'record_ids':JSON.parse($(snippet).attr("data-records-ids")),
                        'modal':$(snippet).attr("data-modal"),
                        'design_editor':JSON.parse($(snippet).attr("data-design-edit")),
                    }
                    if($(snippet).attr("data-snippet-name") == "MegaMenuCategory"){
                        context['extra_info'] = JSON.parse($(snippet).attr("data-extra-info"))
                    }
                    this.rpc('/get_mega_snippet_template', context).then((response)=>{
                        var $template =  $(response['template']).attr("id","as_swiper_slider_as");
                        $(snippet).empty().append($template);
                        if(Object.keys(response.slider_config).length != 0){
                            new Swiper("#as_swiper_slider_as", response.slider_config);
                        }
                        $template.removeAttr("id");
                    })
                }
            }
            this.is_clicked = true;
        }
    }
})

let AlanSliders = publicWidget.Widget.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },
    _getProductSlider:function(){
        for (const product_slider of this.$target) {
            let context = {
                'snippet':$(product_slider).attr("data-snippet-name"),
                'record_ids':JSON.parse($(product_slider).attr("data-records-ids")),
                'modal':$(product_slider).attr("data-modal"),
                'design_editor':JSON.parse($(product_slider).attr("data-design-edit")),
            }
            if(!this.editableMode){
                this.rpc('/get_products_snippet_template', context).then((res)=>{
                    if(this.selector == "[data-snippet-name='CategoryProduct']" || this.selector == "[data-snippet-name='BrandProduct']"){
                        $(product_slider).empty().append(res['template']);
                        var $template = $(product_slider).find('.as_page_swiper')
                        for (let s_templ of $template) {
                            $(s_templ).attr("id",'as_swiper_slider_as');
                            if(Object.keys(res.slider_config).length != 0){
                                new Swiper("#as_swiper_slider_as", res.slider_config);
                            }
                            $(s_templ).removeAttr("id","as_swiper_slider_as")
                        }

                    }else{

                        if('record_ids' in res){
                            $(product_slider).attr("data-records-ids", JSON.stringify(res.record_ids))
                        }
                        var $template =  $(res['template']).attr("id","as_swiper_slider_as");
                        $(product_slider).empty().append($template);
                        if(Object.keys(res.slider_config).length != 0){
                            new Swiper("#as_swiper_slider_as", res.slider_config);
                        }
                        $template.removeAttr("id");
                    }
                    this.trigger_up('widgets_start_request', {$target: $template});
                    this.trigger_up('widgets_start_request', {$target: $(".as_quick_view")});
                    this.trigger_up('widgets_start_request', {$target: $(".as_color_variant")});

                });
            }else{
                $(product_slider).parents(".s_dynamic_snippets").attr("contenteditable",true)
                $(product_slider).empty().append("<div class='text-center'> <h3>"+$(product_slider).attr("data-snippet-name")+"</h3> </div>");
            }
        }
    },
    _tab_change:function(ev){
        this.$target.find(".as-tab-name").removeClass("active");
        let tab_id = $(ev.currentTarget).data('id');
        $(ev.currentTarget).addClass('active');
        if(this.selector == "[data-snippet-name='CategoryProduct']"){
            var slider_tab = "[data-tab-id='category_"+tab_id+"']";
            this.$target.find(".as_category_products").removeClass("active");

        }else{
            var slider_tab = "[data-tab-id='brand_"+tab_id+"']";
            this.$target.find(".as_brand_products").removeClass("active");
        }
        this.$target.find(".as-tab-pane").removeClass("active")
        this.$target.find(slider_tab).addClass("active");
    },
    _get_loader:function(){
        var loader = '<div class="card">\
            <svg class="bd-placeholder-img card-img-top" width="100%" height="180" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Placeholder" preserveAspectRatio="xMidYMid slice" focusable="false">\
                <title>Placeholder</title>\
                <rect width="100%" height="100%" fill="#868e96"></rect>\
            </svg>\
            <div class="card-body">\
                <h5 class="card-title placeholder-glow">\
                    <span class="placeholder col-6"></span>\
                </h5>\
                <p class="card-text placeholder-glow">\
                    <span class="placeholder col-7"></span>\
                    <span class="placeholder col-4"></span>\
                    <span class="placeholder col-4"></span>\
                    <span class="placeholder col-6"></span>\
                    <span class="placeholder col-8"></span>\
                </p>\
                <a href="#" tabindex="-1" class="btn btn-primary disabled placeholder col-6"></a>\
            </div>\
        </div>';
        this.$target.empty().append(loader)
    }
});

publicWidget.registry.ProductWishlist.include({
    selector: '#wrapwrap',
})
publicWidget.registry.ProductComparison.include({
    selector: '#wrapwrap',
})

publicWidget.registry.AlanAddCart = publicWidget.Widget.extend(cartHandlerMixin, VariantMixin, {
    selector: "#wrapwrap",
    events:{
        'click #as_add_to_cart':'async _addToCart',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },
    _addToCart:function(ev){
        ev.preventDefault();
        var def = () => {
            this.isBuyNow = ev.currentTarget.classList.contains('o_we_buy_now');
            const targetSelector = ev.currentTarget.dataset.animationSelector || 'img';
            this.$itemImgContainer = this.$(ev.currentTarget).closest(`:has(${targetSelector})`);
            return this._handleAdd($(ev.currentTarget).closest('form'));
        };
        return def();
    },
    _handleAdd: function ($form) {
        var self = this;
        this.$form = $form;
        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];
        var productReady = this.selectOrCreateProduct(
            $form,
            parseInt($form.find(productSelector.join(', ')).first().val(), 10),
            $form.find('.product_template_id').val(),
            false
        );
        return productReady.then(function (productId) {
            $form.find(productSelector.join(', ')).val(productId);
            self._updateRootProduct($form, productId);
            return self._onProductReady();
        });
    },
    _updateRootProduct($form, productId) {
        this.rootProduct = {
            product_id: productId,
            quantity: parseFloat($form.find('input[name="add_qty"]').val() || 1),
            product_custom_attribute_values: this.getCustomVariantValues($form.find('.js_product')),
            variant_values: this.getSelectedVariantValues($form.find('.js_product')),
            no_variant_attribute_values: this.getNoVariantAttributeValues($form.find('.js_product'))
        };
    },
    _onProductReady: function () {
        return this._submitForm();
    },
    _submitForm: function () {
        const params = this.rootProduct;
        params.add_qty = params.quantity;
        params.product_custom_attribute_values = JSON.stringify(params.product_custom_attribute_values);
        params.no_variant_attribute_values = JSON.stringify(params.no_variant_attribute_values);
        delete params.quantity;
        this.stayOnPageOption = true;
        return this.addToCart(params);
    },
});

publicWidget.registry.alanProductSlider = AlanSliders.extend({
    selector:"[data-snippet-name='ProductSlider']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});


publicWidget.registry.alanBestSellingProduct = AlanSliders.extend({
    selector:"[data-snippet-name='BestSellingProduct']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});

publicWidget.registry.alanLatestProduct = AlanSliders.extend({
    selector:"[data-snippet-name='LatestProduct']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});

publicWidget.registry.alanCategoryProduct = AlanSliders.extend({
    selector:"[data-snippet-name='CategoryProduct']",
    disabledInEditableMode: false,
    events:{
        'click .as-tab-name':'_tab_change'
    },
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});

publicWidget.registry.alanBrandProduct = AlanSliders.extend({
    selector:"[data-snippet-name='BrandProduct']",
    disabledInEditableMode: false,
    events:{
        'click .as-tab-name':'_tab_change'
    },
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});


publicWidget.registry.alanProductBanner = AlanSliders.extend({
    selector:"[data-snippet-name='ProductBanner']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});


publicWidget.registry.alanCategorySlider = AlanSliders.extend({
    selector:"[data-snippet-name='CategorySlider']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});

publicWidget.registry.alanBrandSlider = AlanSliders.extend({
    selector:"[data-snippet-name='BrandSlider']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});

publicWidget.registry.alanBlogSlider = AlanSliders.extend({
    selector:"[data-snippet-name='BlogSlider']",
    disabledInEditableMode: false,
    start:function(){
        this._get_loader()
        this._getProductSlider();
    }
});

export const HeroSlider = publicWidget.Widget.extend({
    selector:".hero_slider",
    disabledInEditableMode: false,
    start:function(){
        var data = new Swiper(".as-slide-swiper", {
            slidesPerView: 1,
            centeredSlides: true,
            slidesPerGroup: 1,
            spaceBetween: 15,
            slideToClickedSlide: true,
            loop: true,
            pagination: {
                el: ".swiper-pagination",
                clickable: true,
            },
            navigation: {
                nextEl: ".swiper-button-next",
                prevEl: ".swiper-button-prev",
            },
              breakpoints: {
                1024: {
                  slidesPerView: 1.60,
                },
              },
        });
    }
});

publicWidget.registry.HeroSlider = HeroSlider;

export default {
    ImgHotSpot: publicWidget.registry.ImgHotSpot,
    HeroSlider: publicWidget.registry.HeroSlider
};
