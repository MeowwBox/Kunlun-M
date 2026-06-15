# -*- coding: utf-8 -*-
import json
import os

FRAMEWORK_NAME = 'Fastify'
DEPENDENCIES = {'package': ['fastify']}


def detect(project_dir, language='javascript'):
    """检测是否为 Fastify 项目"""
    pkg_path = os.path.join(project_dir, 'package.json')
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                return 'fastify' in deps
        except (json.JSONDecodeError, IOError):
            pass
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'request.query',
    'request.body',
    'request.params',
    'request.headers',
    'request.cookies',
    'request.ip',
    'request.hostname',
    'request.protocol',
    'request.url',
]

EXTRA_SINKS = [
    ("reply.view(", [3005]),
    ("reply.redirect(", [3004]),
    ("reply.send(", [3100, 3110]),
    ("reply.file(", [3102, 3106]),
    ("reply.download(", [3102, 3106]),
]
