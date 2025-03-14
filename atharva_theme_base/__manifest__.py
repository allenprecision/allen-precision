# -*- coding: utf-8 -*-
{
    'name': 'Atharva Theme Base',
    'category': 'Base',
    'summary': 'Atharva E-commerce themes Base module',
    'version': '1.8',
    'license': 'OPL-1',
    'author': 'Atharva System',
	'support': 'support@atharvasystem.com',
    'website' : 'https://www.atharvasystem.com',
	'description': """Atharva E-commerce themes Base module""",
    'depends': [
        'website_sale',
        'website_sale_wishlist',
        'website_sale_comparison',
        'website_blog',
        'website_sale_loyalty',
        'stock',
        'crm',
        'sale',
        'delivery',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ppg.xml',
        'data/ir_cron.xml',
        'data/snippet_frames.xml',
        'views/admin/brand_views.xml',
        'views/admin/product_label.xml',
        'views/admin/megamenu_tab.xml',
        'views/admin/pricelist.xml',
        'views/admin/attribute_view.xml',
        'views/admin/menu_tag.xml',
        'views/admin/ppg.xml',
        'views/admin/product_faqs.xml',
        'views/admin/frame.xml',
        'views/admin/product_info.xml',
        'views/admin/product_config.xml',
        'views/megamenu/templates.xml',
        'views/megamenu/advance_megamenu.xml'
     ],
    'assets': {
        'web.assets_frontend': [
            '/atharva_theme_base/static/bundles/swiper/swiper-bundle.min.js',
            '/atharva_theme_base/static/bundles/swiper/swiper-bundle.min.scss',
        ],

        'website.assets_wysiwyg': [
            '/atharva_theme_base/static/bundles/select2/select2.js',
            '/atharva_theme_base/static/bundles/select2/select2.css',
            '/atharva_theme_base/static/bundles/swiper/swiper-bundle.min.js',
            '/atharva_theme_base/static/bundles/swiper/swiper-bundle.min.scss',
            '/atharva_theme_base/static/bundles/sortable/jquery-sortable.js',
        ],

    },
    'price': 6.00,
    'currency': 'EUR',
    'images': ['static/description/as-theme-base.png'],
    'installable': True,
    'application': True
}
