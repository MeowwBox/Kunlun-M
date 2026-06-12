# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Next.js'
DEPENDENCIES = {'package': ['next']}


def detect(project_dir, language='javascript'):
    """检测是否为 Next.js 项目"""
    return os.path.isfile(os.path.join(project_dir, 'next.config.js')) or \
           os.path.isfile(os.path.join(project_dir, 'next.config.mjs'))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = []

EXTRA_SINKS = [
    ("next/redirect(", [3004]),
]
