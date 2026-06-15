# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'MyBatis'
DEPENDENCIES = {'pom': ['mybatis', 'mybatis-spring']}


def detect(project_dir, language='java'):
    """检测是否为 MyBatis 项目"""
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = []

EXTRA_SINKS = [
    ('${', [1004]),
]
