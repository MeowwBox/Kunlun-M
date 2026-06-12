# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'ThinkPHP'
DEPENDENCIES = {'composer': ['topthink/framework']}


def detect(project_dir, language='php'):
    """检测是否为 ThinkPHP 项目"""
    return (os.path.isdir(os.path.join(project_dir, 'thinkphp'))
            or os.path.isfile(os.path.join(project_dir, 'tp5.php')))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = ['Input', 'request', 'I', 'input']
