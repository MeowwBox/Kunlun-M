# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'aiohttp'
DEPENDENCIES = {'requirements': ['aiohttp'], 'pyproject': ['aiohttp']}


def detect(project_dir, language='python'):
    """检测是否为 aiohttp 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'request.query.get',
    'request.match_info.get',
    'request.post',
    'request.json',
]

EXTRA_SINKS = []
