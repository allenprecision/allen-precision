{
    'name': 'Email / Domain Blocklist',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Restrict user creation and eCommerce checkout by email or domain blocklist',
    'description': """
Email / Domain Blocklist
========================
Configurable blocklist of full email addresses and/or domains.

Features:
    * Manage a blocklist of emails and domains from the backend.
    * Block backend user (res.users) creation when login/email is blocked.
    * Block portal signup when the email is blocked.
    * Block eCommerce checkout / order confirmation when the customer email is blocked.
    * Case-insensitive matching, wildcard subdomain support (e.g. *.example.com).
""",
    'author': 'e-BizSoft Inc',
    'license': 'LGPL-3',
    'depends': ['base', 'auth_signup'],
    'data': [
        'security/blocklist_security.xml',
        'security/ir.model.access.csv',
        'views/blocklist_views.xml',
        'data/blocklist_config_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
