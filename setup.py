#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from os import path
from setuptools import setup
  
from cloud_builder.version import __version__

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst')) as readme:
    long_description = readme.read()


config = {
    'name': 'cloud_builder',
    'long_description': long_description,
    'long_description_content_type': 'text/x-rst',
    'python_requires': '>=3.6',
    'description': 'Cloud Builder',
    'author': 'Marcus Schaefer',
    'author_email': 'marcus.schaefer@gmail.com',
    'version': __version__,
    'license' : 'GPLv3+',
    'install_requires': [
        'docopt>=0.6.2',
        'PyYAML',
        'apscheduler',
        'kiwi>=9.21.21',
        'kafka-python',
        'cerberus',
        'requests',
        'psutil'
    ],
    'packages': ['cloud_builder'],
    'entry_points': {
        'console_scripts': [
            'cb-ctl=cloud_builder.cb_ctl:main',
            'cb-info=cloud_builder.cb_info:main',
            'cb-run=cloud_builder.cb_run:main',
            'cb-prepare=cloud_builder.cb_prepare:main',
            'cb-fetch=cloud_builder.cb_fetch:main',
            'cb-scheduler=cloud_builder.cb_scheduler:main'
        ]
    },
    'include_package_data': True,
    'zip_safe': False,
    'classifiers': [
       # classifier: http://pypi.python.org/pypi?%3Aaction=list_classifiers
       'Development Status :: 1 - Planning',
       'Intended Audience :: Developers',
       'License :: OSI Approved :: '
       'GNU General Public License v3 or later (GPLv3+)',
       'Operating System :: POSIX :: Linux',
       'Programming Language :: Python :: 3.6',
       'Programming Language :: Python :: 3.7',
       'Topic :: System :: Operating System',
    ]
}

setup(**config)
