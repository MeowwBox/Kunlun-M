# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'aiohttp'
DEPENDENCIES = {'requirements': ['aiohttp'], 'pyproject': ['aiohttp']}


def detect(project_dir, language='python'):
    """检测是否为 aiohttp 项目"""
    for fname in ['requirements.txt', 'pyproject.toml']:
        dep_path = os.path.join(project_dir, fname)
        if os.path.isfile(dep_path):
            try:
                with open(dep_path, 'r', encoding='utf-8', errors='ignore') as f:
                    if 'aiohttp' in f.read().lower():
                        return True
            except IOError:
                pass
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'request.query.get',
    'request.match_info.get',
    'request.post',
    'request.json',
    'request.headers',
    'request.cookies',
    'request.remote',
]

EXTRA_SINKS = [
    ("response.text", [7008]),
    ("response.write(", [7008]),
    ("aiohttp.ClientSession", [7004]),
]
