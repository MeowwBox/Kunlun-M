# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Struts2'
DEPENDENCIES = {'pom': ['struts2-core']}


def detect(project_dir, language='java'):
    """检测是否为 Struts2 项目"""
    return os.path.isfile(os.path.join(project_dir, 'struts.xml'))


# Struts2 relies on the interceptor stack rather than per-function repair functions,
# so FILTER_FUNCTIONS is intentionally left empty.
FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'ActionContext',
    'ServletActionContext.getRequest',
    'getServlet',
]

EXTRA_SINKS = [
    ("ActionContext.getContext()", [6002]),
    ("ServletActionContext.getRequest()", [6002]),
    # OGNL-related sinks (OGNL injection)
    ("ActionContext.getContext()", [6054]),
    ("ValueStack.findValue(", [6054]),
    ("ValueStack.findString(", [6054]),
    ("OGNL", [6054]),
    # Expression-language injection sinks
    ("TextParseUtil.translateVariables(", [6012]),
    # Open redirect sink
    ("ServletActionContext.getResponse().sendRedirect(", [6015]),
    # Struts2 dynamic method invocation
    ("XWork2", [6056]),
    # Freemarker SSTI / XSS sink
    ("Freemarker", [6002]),
]
