# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Tornado'
DEPENDENCIES = {'requirements': ['tornado'], 'pyproject': ['tornado']}


def detect(project_dir, language='python'):
    """检测是否为 Tornado 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'self.get_argument',
    'self.get_query_argument',
    'self.get_body_argument',
    'self.request.query_arguments',
    'self.get_cookie',
]

EXTRA_SINKS = [
    ("self.render(", [7006]),
]
