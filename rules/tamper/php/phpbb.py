# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'phpBB'
DEPENDENCIES = {'composer': ['phpbb/phpbb']}


def detect(project_dir, language='php'):
    """检测是否为 phpBB 项目"""
    return os.path.isdir(os.path.join(project_dir, 'phpbb'))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = []
