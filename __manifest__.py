{
    'name': 'Miss Rose Analítica',
    'version': '1.0',
    'summary': 'Customer Analysis and Dashboard for Miss Rose',
    'description': 'A module for analyzing customer data and providing an interactive dashboard.',
    'category': 'Sales/CRM',
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'depends': ['base', 'web', 'crm', 'sale', 'account', 'board', 'spreadsheet_dashboard', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        # 'reports/analytics_report.xml',
        # 'views/analytics_views.xml',
        # 'views/settings_views.xml',
        # 'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'missrose_analitica_modulo/static/src/css/style.css',
            # 'missrose_analitica_modulo/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
}
