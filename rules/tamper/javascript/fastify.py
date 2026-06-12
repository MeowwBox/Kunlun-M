# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Fastify'
DEPENDENCIES = {'package': ['fastify']}


def detect(project_dir, language='javascript'):
    """检测是否为 Fastify 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'request.query',
    'request.body',
    'request.params',
    'request.headers',
]

EXTRA_SINKS = [
    ("reply.view(", [3005]),
    ("reply.redirect(", [3004]),
]
