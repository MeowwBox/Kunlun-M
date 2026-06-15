# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Struts2'
DEPENDENCIES = {'pom': ['struts2-core']}


def detect(project_dir, language='java'):
    """检测是否为 Struts2 项目"""
    return os.path.isfile(os.path.join(project_dir, 'struts.xml'))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = []

EXTRA_SINKS = [
    ("ActionContext.getContext()", [6002]),
    ("ServletActionContext.getRequest()", [6002]),
]
