# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Flask'
DEPENDENCIES = {'requirements': ['flask'], 'pyproject': ['flask']}


def detect(project_dir, language='python'):
    """检测是否为 Flask 项目"""
    app_py = os.path.join(project_dir, 'app.py')
    if os.path.isfile(app_py):
        with open(app_py, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if 'flask' in content.lower():
                return True
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = ['flask.request']
