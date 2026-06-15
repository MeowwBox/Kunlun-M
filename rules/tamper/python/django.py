# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Django'
DEPENDENCIES = {'requirements': ['django'], 'pyproject': ['django']}


def detect(project_dir, language='python'):
    """检测是否为 Django 项目"""
    return (os.path.isfile(os.path.join(project_dir, 'manage.py'))
            or os.path.isfile(os.path.join(project_dir, 'settings.py'))
            or os.path.isfile(os.path.join(project_dir, 'wsgi.py')))


FILTER_FUNCTIONS = {}

EXTRA_SINKS = [
    (".objects.raw(", [7002]),
    (".objects.extra(", [7002]),
    ("cursor().execute(", [7002]),
]

CONTROLLED_SOURCES = [
    'request.GET',
    'request.POST',
    'request.FILES',
    'request.body',
    'request.META',
    'request.COOKIES',
    '@request.GET',
]
