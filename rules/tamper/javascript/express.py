# -*- coding: utf-8 -*-
import json
import os

FRAMEWORK_NAME = 'Express'
DEPENDENCIES = {'package': ['express']}


def detect(project_dir, language='javascript'):
    """检测是否为 Express 项目"""
    pkg_path = os.path.join(project_dir, 'package.json')
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                return 'express' in deps
        except (json.JSONDecodeError, IOError):
            pass
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'req.query',
    'req.body',
    'req.params',
    'req.headers',
    'req.cookies',
    'req.files',
    'req.url',
    'req.method',
    'req.ip',
    'req.get',
    'req.param',
]
