odoo.define('shipping_per_product.checkout', function (require) {
'use strict';

    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    require('website_sale_delivery.checkout');
    require('payment.checkout_form');

    var _t = core._t;
    var concurrency = require('web.concurrency');
    var dp = new concurrency.DropPrevious();

    publicWidget.registry.websiteSaleDelivery.include({

        events: _.extend({}, publicWidget.registry.websiteSaleDelivery.prototype.events, {
            "click .sol_delivery_carrier input[name^='delivery_type']" : '_onSOLCarrierClick',
        }),

        init: function(){
            this._super.apply(this, arguments);
            this.del_div = false;
        },

        start:function (){
            var self = this;
            _.each($(".sol_delivery_carrier"), function(SolCarrier, k){
                var $this = $(SolCarrier);
                var SOLCarrier = $this.find("input[name^='delivery_type']:first");
                var carrier_id = SOLCarrier.val();
                var sol_ids = $this.find('.sale_order_line_id').data('sale_order_line_ids');
                var values = {'carrier_id': carrier_id, 'order_lines': sol_ids};
                $('#shipping_per_product_loader').show();
                self._rpc({
                    route: '/shop/sol/update_carrier',
                    params: values,
                }).then(function(result){
                    result['del_div'] = $this;
                    self._handleCarrierUpdateResult(result);
                    SOLCarrier.prop('checked', true);
                });
            });
            return this._super.apply(this, arguments);
        },

        _setCarrierResultBadge: function(result, del_div){
            var $carrierBadge = del_div.find('input[name^="delivery_type"][value=' + result.carrier_id + '] ~ .o_wsale_delivery_badge_price');
            var $check_sol_del = del_div.find('input[name^="line_delivery_name"]');

            if (result.status === true) {
                 // if free delivery (`free_over` field), show 'Free', not '$0'
                 if (result.is_free_delivery) {
                     $carrierBadge.text(_t('Free'));
                 } else {
                     $carrierBadge.html(result.sol_delivery_amount);
                 }
                 $carrierBadge.removeClass('o_wsale_delivery_carrier_error');
                 $check_sol_del.val("SOL Delivery Selected");
            } else {
                $carrierBadge.addClass('o_wsale_delivery_carrier_error');
                $carrierBadge.text(result.error_message);
                $check_sol_del.val("");
            }
        },

        _handleCarrierUpdateResultBadge: function (result) {
            $('#shipping_per_product_loader').hide();
            if(result['del_div']){
                this._setCarrierResultBadge(result, result['del_div']);
            }
            else if(this.del_div){
                this._setCarrierResultBadge(result, this.del_div);
            }
            else{
                this._super.apply(this, arguments);
            }

        },

        _onSOLCarrierClick: function(ev){
            var $this = $(ev.currentTarget);
            var self = this;
            var $payButton = $('button[name="o_payment_submit_button"]');
            $payButton.prop('disabled', true);
            $payButton.data('disabled_reasons', $payButton.data('disabled_reasons') || {});
            // $payButton.data('disabled_reasons').carrier_selection = true;
            var del_div = $this.closest('.sol_delivery_carrier');
            this.del_div = del_div;
            var carrier_id = $this.val();
            var sol_ids = del_div.find('.sale_order_line_id').data('sale_order_line_ids');
            var $empty_sol_del_error = del_div.find('.empty_sol_del_error');
            var values = {'carrier_id': carrier_id, 'order_lines': sol_ids};
            $empty_sol_del_error.hide();
            $('#shipping_per_product_loader').show();
            dp.add(this._rpc({
                route: '/shop/sol/update_carrier',
                params: values,
            })).then(this._handleCarrierUpdateResult.bind(this));
        },
    });

    publicWidget.registry.PaymentCheckoutForm.include({

        _checkSolDelivery: function(event){
            var count = 1
            $('.line_delivery_name').each(function () {
                var $this = $(this);
                var $empty_sol_del_error = $this.closest('.sol_delivery_carrier').find('.empty_sol_del_error');
                if($(this).val() == ''){
                    count = 0;
                    $empty_sol_del_error.show();
                    try{
                        $(".toggle_summary_div.d-none").removeClass("d-none");
                        var thead = $empty_sol_del_error.closest('table');
                        $("html, body").animate({ scrollTop: thead.offset().top }, 500);
                    }
                    catch(err) {
                        console.log("Error:-",err.message);
                    }
                    setTimeout(function() {$empty_sol_del_error.hide()},12000);
                    return false;
                }
            });
            return count;
        },
        _onClickPay: function (ev) {
            ev.preventDefault();
            var result = this._checkSolDelivery();
            if(result == 1){
                this._super.apply(this, arguments);
            }
        }
    });
});
