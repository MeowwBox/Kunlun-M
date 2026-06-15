# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Fiber'
DEPENDENCIES = {'gomod': ['github.com/gofiber/fiber']}


def detect(project_dir, language='go'):
    """检测是否为 Fiber 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'c.Query',
    'c.Params',
    'c.FormValue',
    'c.Body',
    'c.Get',
]

EXTRA_SINKS = [
    ("c.HTML(", [8008]),
    ("c.SendFile(", [8006]),
    ("c.Redirect(", [8013]),
]
