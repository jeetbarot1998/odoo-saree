{
    'name': 'Multi Database Sync',
    'version': '1.0',
    'category': 'Technical',
    'summary': 'Synchronize data between online and local databases',
    'depends': [
        'base',
        'product',
        'point_of_sale',
        'purchase',
        'stock',
        'sale',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/database_connection_views.xml',
        # 'views/sync_views.xml',
        'data/cron_jobs.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}