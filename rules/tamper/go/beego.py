# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Beego'
DEPENDENCIES = {'gomod': ['github.com/astaxie/beego', 'github.com/beego/beego']}


def detect(project_dir, language='go'):
    """检测是否为 Beego 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'c.GetString',
    'c.GetInt',
    'c.GetStrings',
    'c.Input',
    'c.Ctx.Input.Query',
]

EXTRA_SINKS = [
    ("beego.AppConfig.String(", []),
    ("c.Ctx.Output.Body(", [8008]),
]
