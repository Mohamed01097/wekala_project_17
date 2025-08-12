{
    'name': 'Tree Copy Last Line',
    'version': '17.0.1.0.0',
    'category': 'Web',
    'summary': 'Automatically copy last line data when creating new line in editable tree views',
    'description': """
        This module extends the tree view functionality to automatically copy
        the data from the last line when creating a new line using Tab navigation
        in editable tree views.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'tree_copy_last_line/static/src/js/tree_copy_last_line.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}

