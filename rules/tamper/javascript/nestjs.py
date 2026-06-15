# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'NestJS'
DEPENDENCIES = {'package': ['@nestjs/core', '@nestjs/common']}


def detect(project_dir, language='javascript'):
    """检测是否为 NestJS 项目"""
    return os.path.isfile(os.path.join(project_dir, 'nest-cli.json'))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = []

EXTRA_SINKS = [
    ("res.render(", [3005]),
    ("res.redirect(", [3004]),
]
