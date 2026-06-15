# -*- coding: utf-8 -*-
import json
import os

FRAMEWORK_NAME = 'Koa'
DEPENDENCIES = {'package': ['koa']}


def detect(project_dir, language='javascript'):
    """检测是否为 Koa 项目"""
    pkg_path = os.path.join(project_dir, 'package.json')
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                return 'koa' in deps
        except (json.JSONDecodeError, IOError):
            pass
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'ctx.query',
    'ctx.querystring',
    'ctx.request.query',
    'ctx.request.body',
    'ctx.params',
    'ctx.request.header',
    'ctx.ip',
    'ctx.hostname',
    'ctx.host',
    'ctx.protocol',
    'ctx.cookies.get',
    'ctx.headers',
]

EXTRA_SINKS = [
    ("ctx.render(", [3005]),
    ("ctx.redirect(", [3004]),
    ("ctx.body =", [3100, 3110]),
    ("ctx.attachment(", [3102, 3106]),
    ("ctx.redirect(", [3109]),
]
