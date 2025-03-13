/** @odoo-module **/

import Dialog from '@web/legacy/js/core/dialog';
import publicWidget from "@web/legacy/js/public/public_widget";
import '@website_sale/js/website_sale';
import '@website_sale_wishlist/js/website_sale_wishlist';
import '@website_sale_comparison/js/website_sale_comparison';
import { _t } from '@web/core/l10n/translation';
import { debounce } from "@web/core/utils/timing";
const { DateTime } = luxon;
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import VariantMixin from "@website_sale/js/variant_mixin";

//  Color Variant Icon >---------------------------------
const ColorVariantDetails = Dialog.extend({
    init(ele, otps) {
        this.product_id = otps.product_id;
        this._super(ele, {
            backdrop: true,
            size: 'extra-large',
            title:"Color Variant",
            technical: false,
            renderHeader: true,
            renderFooter: false,
        });
        this.rpc = this.bindService("rpc");
    },
    willStart: async function () {
        var template = this.rpc('/get_color_product', { product_id: this.product_id });
        return Promise.all([this._super(...arguments), template]).then((response) => {
            if(response[1] != false){
                this.$content = $(response[1]);
                this.$modal.addClass("as-color-product-modal");
            }
        });
    },
})

export const ShopVariantColor = publicWidget.Widget.extend({
    selector: '.as_color_variant',
    disabledInEditableMode: false,
    events : {
        'mouseenter .as_color_variant_img':'_show_color_image',
        'mouseleave .as_color_variant_img':'_show_default_image',
        'click .as_color_variant_img':'_show_color_variant',
    },
    _show_color_image:function(ev){
        let color_image = $(ev.currentTarget).find("[data-color-image]").attr("data-color-image");
        let $img = this.$target.find(".oe_product_image_img_wrapper > img");
        let default_url = $img.attr("src");
        this.$target.attr("data-default-src",default_url);
        $img.attr("src", color_image);
    },
    _show_default_image:function(ev){
        let default_url = this.$target.attr("data-default-src");
        this.$target.find(".oe_product_image_img_wrapper > img").attr("src", default_url);
    },
    _show_color_variant:function(ev){
        new ColorVariantDetails(this,{ product_id: parseInt($(ev.currentTarget).attr('data-product_tmpl_id'))}).open()
    }
})
publicWidget.registry.ShopVariantColor = ShopVariantColor;
//  Color Variant Icon <---------------------------------

//  Similar Product >---------------------------------
const AlanSimilarProduct = Dialog.extend({
    events:({ 'click .as_close': 'close' }),
    init(ele, otps) {
        this.product_id = otps.product_id;
        this._super(ele, {
            backdrop: true,
            size: 'extra-large',
            technical: false,
            renderHeader: false,
            renderFooter: false,
        });
        this.rpc = this.bindService("rpc");
    },
    willStart: async function () {
        var template = this.rpc('/get_similar_product', { product_id: this.product_id });
        return Promise.all([this._super(...arguments), template]).then((response) => {
            this.$content = $(response[1]);
            this.$modal.addClass("as-similar-product-modal");
        });
    },
    start: function () {
        $(this.$content).appendTo(this.$el);
        return this._super.apply(this, arguments);
    },
})

export const SimilarProduct = publicWidget.Widget.extend({
    selector: '.as_similar_product',
    disabledInEditableMode: false,
    events : {
        'click':'_show_similar',
    },
    _show_similar:function(ev){
        new AlanSimilarProduct(this,{ product_id: parseInt($(ev.currentTarget).attr('data-product_tmpl_id')) }).open();

    }
})
publicWidget.registry.SimilarProduct = SimilarProduct;
//  Similar Product <---------------------------------

//  Scroll Top >---------------------------------
export const ScrolltoTop = publicWidget.Widget.extend({
    'selector': '#wrapwrap',
    'events':{
        'click .as_scroll_to_top, .as-scroll-top' : '_scroll2Top',
        'scroll': '_scroll2TopVisibility',
    },
    _scroll2TopVisibility:function(){
        if(this.$target.scrollTop() > 800){
            this.$target.find(".as_scroll_to_top").addClass("as_scroll_show");
        }else{
            this.$target.find(".as_scroll_to_top").removeClass("as_scroll_show");
        }
    },
    _scroll2Top:function(){
        $("html, body").animate({ scrollTop: 0 }, 500);
    }
});
publicWidget.registry.ScrolltoTop = ScrolltoTop;
//  Scroll Top <---------------------------------

//  Login Popup >---------------------------------
let LoginPopup =  Dialog.extend({
    events: ({
        'click .as_close':'close',
        'click .loginbtn':'_checkAuthentication',
        'click .haveAccount':'_backToLogin',
        'click .signupbtn':'_userSignup',
    }),
    init: function (ele, otps) {
        this._super(ele, {
            backdrop: true,
            size: 'extra-large',
            technical: false,
            renderHeader: false,
            renderFooter: false,
        }, otps);
        this.rpc = this.bindService("rpc");
    },
    willStart: async function(){
        var template = this.rpc('/get_login_popup', {'test':'test'});
        return Promise.all([this._super(...arguments), template]).then((response) => {
            this.$content = $(response[1]);
            this.$modal.addClass("as-login-modal");
        });
    },
    start: function () {
        $(this.$content).appendTo(this.$el);
        return this._super.apply(this, arguments);
    },
    _checkAuthentication:function(ev){

        var cr = this;
        const login = this.$el.find("#login").val();
        const password = this.$el.find("#password").val();
        if(login.trim() != "" && password.trim() != ""){
            ev.preventDefault();
            return this.rpc("/alan/login/authenticate", { "login":login, "password":password }).then(function (result) {
                if(result["login_success"] == true){
                    window.location.reload();
                }
                else if("error" in result){
                    cr.$el.find("#errormsg").css("display","block").empty().append(result["error"]);
                }
            });
        }
    },
    _userSignup:function(ev){
        var cr = this;
        const logins = cr.$el.find("#logins").val();
        const passwords = cr.$el.find("#passwords").val();
        const names = cr.$el.find("#names").val();
        const confirm_passwords = cr.$el.find("#confirm_passwords").val();
        const token = cr.$el.find("#token").val()
        if(logins.trim() != "" && passwords.trim() != ""
            && confirm_passwords.trim() != "" && names.trim() != ""){
            ev.preventDefault();
            return this.rpc("/alan/signup/authenticate",{
                    "login":logins,
                    "name":names,
                    "password":passwords,
                    "confirm_password":confirm_passwords,
                    "token":token
                    }
            ).then(function (result) {
                if("error" in result){
                    cr.$el.find("#errors").css("display","block").empty().append(result["error"])
                }
                else if(result["signup_success"] == true){
                    window.location.reload();
                }
            });
        }
    },
    _backToLogin:function(){
        this.$el.find("#as-login").click();
    },
});

export const LoginPopups = publicWidget.Widget.extend({
    selector: ".as_login_popup",
    events:{
        'click':'_show_login_popup',
    },
    _show_login_popup:function(ev){
        ev.preventDefault();
        this.LoginPopup = new LoginPopup(this, {});
        this.LoginPopup.open();
    }
});

publicWidget.registry.LoginPopup = LoginPopups;
//  Login Popup <---------------------------------

//  Quick View >---------------------------------
const AlanQuickView = Dialog.extend({
    events:({ 'click .as_close': 'close',
    }),
    init(ele, otps) {
        this.product_id = otps.product_id;
        this._super(ele, {
            backdrop: true,
            size: 'extra-large',
            technical: false,
            renderHeader: false,
            renderFooter: false,
        });
        this.rpc = this.bindService("rpc");
    },
    QuickViewLOad:function(){
        var self = this
        var template = this.rpc('/get_quick_view', { product_id: this.product_id }).then((response) => {
            self.$content = $(response);
            self.$modal.addClass("as-quick-view-modal");
            self.$el.find('.as_spinner').addClass('d-none');
            $(self.$content).appendTo(self.$el);
            self.trigger_up('widgets_start_request', {
                $target: self.$content,
            });
        });

    },
    start: function () {
        this.QuickViewLOad();
        $('<div class="as_spinner ratio ratio-21x9" role="status"><div class="d-flex align-items-center justify-content-center"><span class="spinner-border"></span></div></div>').appendTo(this.$el);
        return this._super.apply(this, arguments);
    },
});

export const QuickView = publicWidget.Widget.extend({
    selector: ".as_quick_view",
    events:{
        'click':'_show_quick_view',
    },
    _show_quick_view:function(ev){
        new AlanQuickView(this,{ product_id: parseInt($(ev.currentTarget).attr('data-product_tmpl_id')) }).open();
    }
});

publicWidget.registry.QuickView = QuickView;
//  Quick View <---------------------------------

//  Load More >---------------------------------
export const AjaxProductLoad = publicWidget.Widget.extend({
    selector:".as_shop_page",
    disabledInEditableMode: false,
    events:{
        'click #loadMoreproducts':'_loadProduct'
    },

    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },

    InitLoadProducts:function(){
        var self = this;
        this.next_products = false;
        this.pager = false;
        this.rmn_ids = []
        var $next_page = $(".alan_pager").find("li.active").next();
        var prd_ids = $next_page.data('prd_ids')
        let next_url = $next_page.find("a").attr("href");
        if(next_url == undefined || next_url == "" || prd_ids == undefined || prd_ids == ""){
            this.$target.find("#loadMoreproducts").hide();
            this.$target.find(".all_loaded").removeClass('d-none').empty().append(_t("All products are loaded."))
        }
        else{
            var ppr = $next_page.data('ppr')
            var $lasttr = this.$target.find(".o_wsale_products_grid_table_wrapper").find("tbody tr:last").find('td')
            if ($lasttr.length < ppr){
                for (let i = 0; i < $lasttr.length; i++) {
                    self.rmn_ids.push(parseInt($($lasttr[i]).find('.product_ref_id').val()))
                }
            }
            var products = this.$target.find(".o_wsale_products_grid_table_wrapper").find('input.product_ref_id').map(function(){return parseInt($(this).val());}).get();
            var all_prds = $.merge(self.rmn_ids, prd_ids)
            this.rpc("/nextpage/products",{
                        'product_ids': all_prds,
                        'products': products,
                        'ppr': ppr,
                    }
            ).then(function (result) {
                if(result){
                    self.next_products = result;
                }
            });
        }
    },

    _loadProduct:function(){
        if(this.next_products != false){
            var $active_page = $(".alan_pager").find("li.active");
            var $next_page = $(".alan_pager").find("li.active").next();
            var ppr = $next_page.data('ppr')
            var $lasttr = this.$target.find(".o_wsale_products_grid_table_wrapper").find("tbody tr:last").find('td')
            if ($lasttr.length < ppr){
                this.$target.find(".o_wsale_products_grid_table_wrapper").find("tbody tr:last").remove()
            }
            this.$target.find(".o_wsale_products_grid_table_wrapper").find("tbody").append(this.next_products);
            $active_page.removeClass('active');
            $next_page.addClass('active');
        }
        this.InitLoadProducts();
        this.trigger_up('widgets_start_request', {
            $target:$('.as_offer_timer')
        });
        this.trigger_up('widgets_start_request', {
            $target:$('.as_quick_view'),
        });
        this.trigger_up('widgets_start_request', {
            $target:$('.o_wsale_product_grid_wrapper'),
        });
        this.trigger_up('widgets_start_request', {
            $target:$('.as_similar_product'),
        });
    },
    start:function(){
        this.InitLoadProducts();

    }
});
publicWidget.registry.AjaxProductLoad = AjaxProductLoad;
//  Load More <---------------------------------

//  Attribute Search >---------------------------------
publicWidget.registry.WebsiteSale.include({
    _onChangeAttribute: function (ev) {
        if (!ev.isDefaultPrevented() && !$(ev.target).hasClass('as_filter_search')) {
            ev.preventDefault();
            const productGrid = this.el.querySelector(".o_wsale_products_grid_table_wrapper");
            if (productGrid) {
                productGrid.classList.add("opacity-50");
            }
            $(ev.currentTarget).closest("form").submit();
        }
    },
});

export const AttributeSearch = publicWidget.Widget.extend({
    selector:'.as_filter_search',
    events:{
        'keyup':'_search_attribute'
    },
    _search_attribute(ev){
        let curr_val = this.$target.val().toLowerCase();
        let $attrs = $(ev.target).parents(".accordion-item").find("label.form-check-label");
        let $color = $(ev.target).parents(".accordion-item").find("label.css_attribute_color");
        let $brands = $(ev.target).parents(".accordion-item").find("label.as_brand_attr_image");

        if($attrs.length > 0){
            for (const iter of $attrs) {
                let attr = $(iter).text().toLowerCase();
                if(!attr.includes(curr_val)){
                    $(iter).parent('.form-check').addClass("d-none")
                }else{
                    $(iter).parent('.form-check').removeClass("d-none")
                }
            }
        }
        if ($color.length > 0){
            for (const iter of $color) {
                let attr = $(iter).find("input").attr("title").toLowerCase();
                if(!attr.includes(curr_val)){
                    $(iter).addClass("d-none")
                }else{
                    $(iter).removeClass("d-none")
                }
            }
        }
        if ($brands.length > 0){
            for (const iter of $brands) {
                let attr = $(iter).attr('data-name').toLowerCase();
                if(!attr.includes(curr_val)){
                    $(iter).addClass("d-none")
                }else{
                    $(iter).removeClass("d-none")
                }
            }
        }
    }
})
publicWidget.registry.AttributeSearch = AttributeSearch;
//  Attribute Search <---------------------------------

//  Offer Timer >---------------------------------
export const OfferTimer =  publicWidget.Widget.extend({
    selector: ".as_offer_timer",

    disabledInEditableMode: false,
    start:function(){
        if(this.$target.attr("data-offer") != undefined && this.$target.attr("data-offer") != 'false'){
            var self = this;
            var asOfferTimer;
            var offerTimer = function(){
                if(!self.editableMode){
                    var offerTime = deserializeDateTime(self.$target.attr("data-offer"));
                    var currentTime = DateTime.now();
                    var duration = offerTime.ts - currentTime.ts
                    if(duration < 0){
                        clearInterval(asOfferTimer);
                        self.$target.empty();
                    }
                    else{
                        var days = Math.floor(duration / (1000 * 60 * 60 * 24));
                        var hours = Math.floor((duration / (1000 * 60 * 60)) % 24)
                        var minutes = Math.floor((duration / 1000 / 60) % 60)
                        var seconds = Math.floor((duration / 1000) % 60)
                        days = days < 10 ? "0" + days : days;
                        hours = hours < 10 ? "0" + hours : hours;
                        minutes = minutes < 10 ? "0" + minutes : minutes;
                        seconds = seconds < 10 ? "0" + seconds : seconds;
                        self.$target.removeClass("d-none");
                        self.$target.empty().html("<ul>\
                            <li>\
                                <label>"+ days +"</label>\
                                <span>Days</span>\
                            </li>\
                            <li>\
                                <label>"+ hours +"</label>\
                                <span>Hours</span>\
                            </li>\
                            <li>\
                                <label>"+ minutes +"</label>\
                                <span>Minutes</span>\
                            </li>\
                            <li>\
                                <label>"+ seconds +"</label>\
                                <span>Seconds</span>\
                            </li>\
                        </ul>");
                    }
                }else{
                    let timer_info = sessionStorage.getItem("as_timer_ids");
                    if(timer_info !=  undefined){
                        let timer_ids = JSON.parse(timer_info)
                        for (const time_id of timer_ids) {
                            clearInterval(time_id);
                        }
                    }
                    self.$target.empty();
                }
            }
            offerTimer();
            asOfferTimer = setInterval(function () { offerTimer() }, 1000);
            let get_timer_info = sessionStorage.getItem("as_timer_ids");
            var get_timer_ids = [];
            if(get_timer_info != undefined){
                get_timer_ids = JSON.parse(get_timer_info);
            }
            if(get_timer_ids.indexOf(asOfferTimer) == -1){
                get_timer_ids.push(asOfferTimer)
                sessionStorage.setItem("as_timer_ids", JSON.stringify(get_timer_ids))
            }
        }
    }
});
publicWidget.registry.OfferTimer = OfferTimer;
//  Offer Timer <---------------------------------

//  Shop Rating >---------------------------------
// export const ShopRating = publicWidget.Widget.extend({
//     selector: '.as_product_rating',
//     disabledInEditableMode: false,
//     events:{
//         'mouseenter ':'_show_ratings_info',
//         'mouseleave ':'_show_default_rating',
//     },
//     _show_ratings_info:function()
//     {
//         if(this.$target.find('#rating_reviews').val()){
//             var ratings_reviews_info = "<div style='color: black;font-weight: 400;'>"+ this.$target.find('#rating_reviews').val() +" Reviews </div>";
//             this.$target.popover({
//                 html: true,
//                 container: 'body',
//                 content:ratings_reviews_info,
//             }).popover('show');
//         }
//     },
//     _show_default_rating:function()
//     {
//         this.$target.popover('dispose');
//     },
// })
// publicWidget.registry.ShopRating = ShopRating;
//  Shop Rating <---------------------------------

//  Clear Filter >---------------------------------
export const AlanClearFilter = publicWidget.Widget.extend({
    selector:".o_wsale_products_page",
    events:{
        'click .as-clear-filter':'_clearFilter',
    },
    _clearFilter:function(ev){
        const fieldName = $(ev.currentTarget).data("name");
        const fieldValue = $(ev.currentTarget).data("value");
        const $filterForm = this.$target.find("form.js_attributes");
        const $input = $filterForm.find('input[name="'+fieldName+'"][value="' + fieldValue + '"]');
        if($input.length == 0){
            const $option = $filterForm.find('option[value=' + fieldValue + ']');
            $option.closest('select').val('').trigger("change");
        }
        $input.prop('checked', false);
        $input.trigger("change");
    },
    start: function () {
        new Swiper(".as_wsale_filmstip", {
            slidesPerView: "auto",
            spaceBetween: 10,
            navigation: {
              nextEl: ".swiper-button-next",
              prevEl: ".swiper-button-prev",
            },
        });
        return this._super.apply(this, arguments);
    },
});
publicWidget.registry.alanClearFilter = AlanClearFilter;
//  Clear Filter  <---------------------------------

//  Mini Cart >---------------------------------
const AlanMiniCartProduct = Dialog.extend({
    events:({
    'click .as_close': 'close',
    'click a.js_add_cart_json':'_onUpdateQty',
    'change input.js_quantity[data-product-id]': '_onChangeQty',
    'click .js_delete_product':'_onClickRemoveProduct',
    'click .as_clr_cart':'_asClearCart',
    'click a.js_add_suggested_products': '_onClickSuggestedProduct',
    }),
    init(ele, otps) {
        this._super(ele, {
            backdrop: true,
            size: 'extra-large',
            technical: false,
            renderHeader: false,
            renderFooter: false,
        });
        this.rpc = this.bindService("rpc");
        this._changeCartQuantity = debounce(this._changeCartQuantity.bind(this), 500);
    },
    willStart: async function () {
        var template = this.rpc('/get_mini_cart', { });
        return Promise.all([this._super(...arguments), template]).then((response) => {
            this.$content = $(response[1]['as_mini_cart']);
            this.$modal.addClass("as-mini-cart-modal");
        });
    },
    _onUpdateQty: function(ev){
        VariantMixin.onClickAddCartJSON(ev);
    },
    _changeCartQuantity: function ($input, value, $dom_optional, line_id, productIDs,productList, target) {
        $input.data('update_change', true);
        this.rpc("/shop/cart/update_json", {
            line_id: line_id,
            product_id: parseInt($input.data('product-id'), 10),
            set_qty: value,
            display: true,
        }).then((data) => {
            $input.data('update_change', false);
            if (!data.cart_quantity) {
                $(target).parents().find(('.js_delete_product')).trigger('click');
            }
            else{
                $input.val(data.quantity);
                $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).text(data.quantity);
                this.$el.find(".as-qty").empty().append(data.cart_quantity);
                this.alanUpdateCartNavBar(data);
                this.$el.find(".as-shipping-details").empty().append(data['theme_alan.as_shipping_view_template']);
            }
        });
    },
    _onChangeQty: function (ev){
        var $input = $(ev.currentTarget);
        if ($input.data('update_change')) {
            return;
        }
        var value = parseInt($input.val() || 0, 10);
        var $dom = $input.closest('tr');
        var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
        var line_id = parseInt($input.data('line-id'), 10);
        var productIDs = [parseInt($input.data('product-id'), 10)];
        var productList = $(ev.currentTarget).data('productList')
        if(productList && productList.includes(Number($(ev.currentTarget).data('productId')))){
            var line_class = '.sale_line_' + Number($(ev.currentTarget).data('productId'))
            $(line_class).val(Number($(line_class).val())+1).trigger('change')
        }
        else{
            this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs,productList, ev.currentTarget);
        }
    },
    _onClickRemoveProduct: function (ev) {
        ev.preventDefault();
        if($('.as-mini-cart-products').find('li.as-mc-media').length == 1){
            this._asClearCart();
        }
        else{
            $(ev.currentTarget).siblings().find('.js_quantity').val(0).trigger("change");
        }
    },
    _asClearCart:function(){
        this.rpc('/as_clear_cart',{}).then((response) => {
            $(".cart_body").replaceWith(response['empty_mini_cart']);
        });
        this.$el.find(".as-qty").empty().append(0);
        $(".my_cart_quantity").text("0")
        $(".as_clr_cart").remove()
    },

    alanUpdateCartNavBar(data) {
        sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
        $(".my_cart_quantity")
            .parents('li.o_wsale_my_cart').removeClass('d-none').end().toggleClass('d-none', data.cart_quantity === 0)
            .addClass('o_mycart_zoom_animation').delay(300)
            .queue(function () {
                $(this)
                    .attr('title', data.warning)
                    .text(data.cart_quantity || '')
                    .removeClass('o_mycart_zoom_animation')
                    .dequeue();
            });
        $("#cart_total").replaceWith(data['website_sale.total']);
        this.rpc('/get_mini_cart', {}).then((response) => {
            $(".as-mini-main-cart").replaceWith(response['as_mini_cart_lines']);
        });
        if (data.cart_ready) {
            document.querySelector("a[name='website_sale_main_button']")?.classList.remove('disabled');
        } else {
            document.querySelector("a[name='website_sale_main_button']")?.classList.add('disabled');
        }
    },
    _onClickSuggestedProduct: function (ev) {
        $(ev.currentTarget).prev('input').val(1).trigger('change');
    },
})

export const MiniCart = publicWidget.Widget.extend({
    selector: ".as_mini_cart",
    events:{
        'click':'_show_mini_cart',
    },
    _show_mini_cart:function(ev){
        ev.preventDefault();
        new AlanMiniCartProduct(this,{}).open();
    },
});
publicWidget.registry.MiniCart = MiniCart;
//  Mini Cart <---------------------------------

export default {
    ShopVariantColor: publicWidget.registry.ShopVariantColor,
    SimilarProduct: publicWidget.registry.SimilarProduct,
    ScrolltoTop: publicWidget.registry.ScrolltoTop,
    MiniCart:publicWidget.registry.MiniCart,
    AjaxProductLoad: publicWidget.registry.AjaxProductLoad,
    LoginPopup: publicWidget.registry.LoginPopup,
    AttributeSearch:publicWidget.registry.AttributeSearch,
    OfferTimer: publicWidget.registry.OfferTimer,
    QuickView:publicWidget.registry.QuickView,
    ShopRating:publicWidget.registry.ShopRating,
    AlanClearFilter:publicWidget.registry.alanClearFilter,
};
