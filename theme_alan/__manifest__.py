# -*- encoding: utf-8 -*-
{
    'name': 'Theme Alan',
    'category': 'Theme/eCommerce',
    'sequence': 1000,
    'version': '2.0.3.3',
    'license': 'OPL-1',
    'author': 'Atharva System',
    'support': 'support@atharvasystem.com',
    'website' : 'https://www.atharvasystem.com',
    'live_test_url': 'https://alan-v15.atharvasystem.com',
    'description': """Theme Alan is one of the most powerful, amazing and flexible theme on Odoo store""",
    'summary': 'Theme Alan is one of the most powerful, amazing and flexible theme on Odoo store.',
    'depends': ['atharva_theme_base'],
    'data': [
        'views/headers/headers.xml',
        'views/headers/switch.xml',
        'views/footers/footers.xml',
        'views/footers/switch.xml',
        'views/megamenu.xml',
        'views/product_rating.xml',
        'views/product_label.xml',
        'views/quick_add_to_cart.xml',
        'views/quick_view.xml',
        'views/shop_layout.xml',
        'views/product_brand.xml',
        'views/product_details.xml',
        'views/product_tags.xml',
        'views/menu_tag.xml',
        'views/shop.xml',
        'views/b2b_mode.xml',
        'views/similar_product.xml',
        'views/login_popup.xml',
        'views/color_tag_view.xml',
        'views/alan_button.xml',
        'views/snippets/s_alan_snippet_builder.xml',
        'views/snippets/s_brand_slider.xml',
        'views/snippets/s_brand_product_slider.xml',
        'views/snippets/s_category_slider.xml',
        'views/snippets/s_category_product_slider.xml',
        'views/snippets/s_product_slider.xml',
        'views/snippets/s_product_banner_slider.xml',
        'views/snippets/s_product_variant_slider.xml',
        'views/snippets/s_best_seller_product.xml',
        'views/snippets/s_latest_product_slider.xml',
        'views/snippets/s_product_offer_snippet.xml',
        'views/snippets/s_product_offer_slider.xml',
        'views/snippets/s_categ_product_slider.xml',
        'views/snippets/s_category_grid_snippet.xml',
        'views/snippets/s_faq_snippet.xml',
        'views/snippets/s_blog_slider.xml',
        'views/snippets/s_image_gallery.xml',
        'views/snippets/slider_and_grid/brand_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/category_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/product_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/product_banner_slider_layout.xml',
        'views/snippets/slider_and_grid/product_variant_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/best_seller_product_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/latest_product_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/category_product_slider_layout.xml',
        'views/snippets/slider_and_grid/category_grid_layout.xml',
        'views/snippets/slider_and_grid/blog_slider_grid_layout.xml',
        'views/snippets/slider_and_grid/product_offer_snippet_template.xml',
        'views/snippets/slider_and_grid/product_offer_slider_layout.xml',
        'views/snippets/slider_and_grid/image_gallery_snippet_layout.xml',
        'views/snippets/slider_and_grid/snippet_base_templates.xml',
        'views/snippets/s_image_hotspot.xml',
        'views/snippets/s_offer_banner.xml',
        'views/brands.xml',
        'views/quick_load_product.xml',
        'views/buttons.xml',
        'views/alan_wishlist.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            "theme_alan/static/src/scss/variables.scss",
            "theme_alan/static/src/scss/shop/*.scss",
            "theme_alan/static/src/scss/headers/*.scss",
            "theme_alan/static/src/scss/footers/*.scss",
            "theme_alan/static/src/scss/buttons.scss",
            'theme_alan/static/src/js/snippets/**/*.scss',
            'theme_alan/static/src/js/snippets/**/000.js',
            'theme_alan/static/src/scss/base.scss',
            'theme_alan/static/src/scss/mini-cart.scss',
            'theme_alan/static/src/scss/shop.scss',
            'theme_alan/static/src/scss/clear-filter.scss',
            'theme_alan/static/src/scss/modal.scss',
            'theme_alan/static/src/scss/sticky-cart.scss',
            'theme_alan/static/src/scss/bubble-category.scss',
            'theme_alan/static/src/scss/product-detail.scss',
            'theme_alan/static/src/scss/mega-menu.scss',
            'theme_alan/static/src/scss/brand-page.scss',
            'theme_alan/static/src/scss/shop/full-layout.scss',
            'theme_alan/static/src/scss/headers/common_header.scss',
            'theme_alan/static/src/scss/footers/common_footer.scss',
            'theme_alan/static/src/js/base/quickProdView.js',
            'theme_alan/static/src/js/frontend/alan_search.js',
            'theme_alan/static/src/js/frontend/main.js',
            'theme_alan/static/src/js/base/miniCartDialog.js',
            'theme_alan/static/src/js/frontend/quick_modal.js',
            'theme_alan/static/src/js/frontend/quick_attribute_search.js',
        ],
        'web._assets_primary_variables': [
            'theme_alan/static/src/scss/assets_primary_variables/alan_primary_variables.scss'
        ],
        'web._assets_frontend_helpers': [
            'theme_alan/static/src/scss/assets_frontend_helpers/alan_frontend_helpers.scss',
        ],
        'web.assets_common': [
            'theme_alan/static/src/js/base/coreMixins.js',
            'theme_alan/static/src/js/base/common_modal.js',
        ],
        'website.assets_editor':[
            'theme_alan/static/src/scss/editor_popup.scss',
            'theme_alan/static/src/js/base/megaDialog.js',
            'theme_alan/static/src/js/base/recordSelector.js',
            'theme_alan/static/src/js/editor/options.js',
            'theme_alan/static/src/js/base/brandCatDialog.js',
            'theme_alan/static/src/js/base/productDialog.js',
            'theme_alan/static/src/js/base/offerDialog.js',
            'theme_alan/static/src/js/base/catProductDialog.js',
            'theme_alan/static/src/js/base/catGridDialog.js',
            'theme_alan/static/src/js/snippets/**/options.js',
        ],
        'web.assets_qweb': [
            'theme_alan/static/src/xml/snippets/*.xml',
        ],
    },
    'snippet_lists': {
        'homepage': ['s_cover', 's_text_image', 's_image_text', 's_masonry_block', 's_call_to_action', 's_picture'],
        'about_us': ['s_text_image', 's_image_text', 's_title', 's_company_team'],
        'our_services': ['s_three_columns', 's_quotes_carousel', 's_references'],
        'pricing': ['s_comparisons'],
        'privacy_policy': ['s_faq_collapse'],
    },
    'price': 195.00,
    'currency': 'EUR',
    'images': ['static/description/alan_description.png','static/description/alan_screenshot.gif'],
    'application': False,
    'auto_install': False,
}
