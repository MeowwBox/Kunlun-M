# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Koa'
DEPENDENCIES = {'package': ['koa']}


def detect(project_dir, language='javascript'):
    """检测是否为 Koa 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'ctx.query',
    'ctx.querystring',
    'ctx.request.query',
    'ctx.request.body',
    'ctx.params',
    'ctx.request.header',
]

EXTRA_SINKS = [
    ("ctx.render(", [3005]),
    ("ctx.redirect(", [3004]),
]
