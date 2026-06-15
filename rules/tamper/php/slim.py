# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Slim'
DEPENDENCIES = {'composer': ['slim/slim']}


def detect(project_dir, language='php'):
    """检测是否为 Slim 项目"""
    return os.path.isfile(os.path.join(project_dir, 'public', 'index.php'))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    '$request->getParsedBody',
    '$request->getQueryParams',
    '$request->getParams',
    '$request->getParam',
    '$args',
]

EXTRA_SINKS = []
