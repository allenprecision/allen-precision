/** @odoo-module **/

import Dialog from '@web/legacy/js/core/dialog';
import publicWidget from "@web/legacy/js/public/public_widget";


export const ProductDetailInfo = publicWidget.Widget.extend({
    selector:".as-product-detail",
    events:{
        'mouseenter .as-pager-prod':'_show_pager_product_info',
        'mouseleave .as-pager-prod':'_hide_pager_product_info',
        'scroll':'_stickyCart',
        'click .as_sticky_action':'_sticky_btn',
    },
    init: function () {
        this._super.apply(this, arguments);
        this.rpc = this.bindService("rpc");
    },
    start: function () {
        new Swiper(".as-al-ass-swiper", {
            slidesPerView: 1.75,
            spaceBetween: 10,
            navigation: {
              nextEl: ".swiper-button-ass-next",
              prevEl: ".swiper-button-ass-prev",
            },
            breakpoints: {
              640: {
                slidesPerView: 2,
                spaceBetween: 24,
              },
              768: {
                slidesPerView: 3,
                spaceBetween: 24,
              },
              1024: {
                slidesPerView: 4,
                spaceBetween: 24,
              },

            },
        });

        new Swiper(".as-al-alt-swiper", {
            slidesPerView: 1.75,
            spaceBetween: 10,
            navigation: {
              nextEl: ".swiper-button-alt-next",
              prevEl: ".swiper-button-alt-prev",
            },
            breakpoints: {
              640: {
                slidesPerView: 2,
                spaceBetween: 24,
              },
              768: {
                slidesPerView: 3,
                spaceBetween: 24,
              },
              1024: {
                slidesPerView: 4,
                spaceBetween: 24,
              },

            },
        });
        this.trigger_up('widgets_start_request', {$target: $(".as_color_variant")});

        return this._super.apply(this, arguments);
    },
    _show_pager_product_info(ev){
        if($(ev.currentTarget).attr('id') == "as-pre-prod-info"){
            this.$target.find(".as-pre-prod-info").removeClass("d-none");
        }else{
            this.$target.find(".as-next-prod-info").removeClass("d-none");
        }
    },
    _hide_pager_product_info(ev){
        this.$target.find(".as-pager-prod-info").addClass("d-none")
    },
    _stickyCart:function(ev){
        var cr = this;
        var addToCartBtns = cr.$target.find('#add_to_cart');
        if(cr.$target.find('.as-sticky-cart-active').length != 0 && addToCartBtns.length != 0){
            const top = cr.$target.find('#add_to_cart').offset().top;
            const bottom = cr.$target.find('#add_to_cart').offset().top + cr.$target.find('#add_to_cart').outerHeight();
            const bottom_screen = $(window).scrollTop() + $(window).innerHeight();
            const top_screen = $(window).scrollTop();
            if ((bottom_screen > top) && (top_screen < bottom)){
                if(cr.$target.find('.as-product-sticky-cart').hasClass("as-stikcy-show")){
                    cr.$target.find('.as-product-sticky-cart').removeClass("as-stikcy-show");
                }
            } else {
                if(top < 0){
                    if(!cr.$target.find('.as-product-sticky-cart').hasClass("as-stikcy-show")){
                        cr.$target.find('.as-product-sticky-cart').addClass("as-stikcy-show");
                    }
                }
            }
        }
        var offset = 450;
        var $back_to_top = $('.as-scroll-to-top');
        ($('#wrapwrap').scrollTop() > offset) ? $back_to_top.addClass('as-bt-visible'): $back_to_top.removeClass('as-bt-visible');
    },
    _sticky_btn:function(ev){
        this.$target.find($(ev.target).data('target_id')).trigger("click");
    },
})

publicWidget.registry.ProductDetailInfo = ProductDetailInfo;


let AlanAdvanceInfo = Dialog.extend({
    events:({ 'click .as_close': 'close',
    }),
    init(ele, otps) {
        this.advance_info_id = otps.advance_info_id;
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
        var template = this.rpc('/get_advance_info', { advance_info_id: this.advance_info_id });
        return Promise.all([this._super(...arguments), template]).then((response) => {
            this.$content = $("<div>" + response[1] + "</div>");
        });
    },

    start: function () {
        $(this.$content).appendTo(this.$el);
        this.trigger_up('widgets_start_request', {
            $target: this.$content,
        });
        return this._super.apply(this, arguments);
    },
});

export const ProductAdvanceInfo = publicWidget.Widget.extend({
    "selector": ".show_advance_product",
    events : {
        "click": "_show_advance_info_dialog"
    },
    _show_advance_info_dialog: function(){
        new AlanAdvanceInfo(this, { advance_info_id: parseInt(this.$target.attr("data-info_id")) }).open();
    }
});
publicWidget.registry.ProductAdvanceInfo = ProductAdvanceInfo;

const ProductQueriesInfo = Dialog.extend({
    events:({
        'click .as_close': 'close',
        'click .send_questions': '_sendClick',
        'keyup textarea.msg': '_onChangeInput',
    }),
    init(ele, otps) {
        this.product_id = otps.product_id;
        this.user_id = otps.user_id;
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
        var template = this.rpc('/product_queries',{product_id: this.product_id });
        return Promise.all([this._super(...arguments), template]).then((response) => {
            if (response[1]){
                this.$content = $(response[1]);
                this.$modal.addClass("as-queries-modal");
            }
            else{
                $('.query-msg')[0].classList.remove("d-none");
                this.close()
            }
        });
    },
    start: function () {
        return this._super.apply(this, arguments);
    },
    _sendClick: function(ev){
        var self = this
        var email = $("#email").val();
        var message = $("#message").val()
        var user_id = $("#customer_id").val()
        let radios = $('.ContactPreference');
        let selectedValue = '';
        for (let i = 0; i < radios.length; i++) {
            if (radios[i].checked) {
                selectedValue = radios[i].id;
                break;
            }
        }
        if (message == '') {
            $(".msg").addClass("border").addClass("border-danger")
        }
        var context = { message: message,user_id:user_id,email:email,product_id:this.product_id,contact_preference:selectedValue}

        if (message){
            return this.rpc('/send_queries_mail', context).then((response) => {
            }).then(function() {
                $(".dialog-container").hide();
                $("#thank-you").removeClass("o_hidden");
                setTimeout(function() {
                    self.close()
                  }, 2000);
            })
        }
    },
    _onChangeInput:function(){
        $(".msg").removeClass("border").removeClass("border-danger")
    },
})



export const ProductQueries = publicWidget.Widget.extend({
    selector: '.product_queries',
    disabledInEditableMode: false,
    events : {
        'click #any_queries': '_onClickQueries',
    },
    _onClickQueries:function(){
        let inputproduct = $("#product").val();
        let inputuser = $("#user").val();
        new ProductQueriesInfo(this,{ product_id: inputproduct,user_id:inputuser}).open();
    }
});
publicWidget.registry.ProductQueries = ProductQueries;

export default {
    ProductDetailInfo: publicWidget.registry.ProductDetailInfo,
    ProductAdvanceInfo: publicWidget.registry.ProductAdvanceInfo,
    ProductQueries: publicWidget.registry.ProductQueries,
};
