# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'FastAPI'
DEPENDENCIES = {'requirements': ['fastapi'], 'pyproject': ['fastapi']}


def detect(project_dir, language='python'):
    """检测是否为 FastAPI 项目"""
    # FastAPI 通常没有特征文件，依赖依赖检测
    return False


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = []

EXTRA_SINKS = [
    ("Jinja2Templates(", [7006]),
    ("TemplateResponse(", [7006]),
]
