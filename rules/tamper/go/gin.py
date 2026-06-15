# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Gin'
DEPENDENCIES = {'gomod': ['github.com/gin-gonic/gin']}


def detect(project_dir, language='go'):
    """检测是否为 Gin 项目"""
    go_mod = os.path.join(project_dir, 'go.mod')
    if os.path.isfile(go_mod):
        try:
            with open(go_mod, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'gin' in content:
                    return True
        except IOError:
            pass
    return False


FILTER_FUNCTIONS = {}

EXTRA_SINKS = [
    ("c.HTML(", [8008]),
    ("c.File(", [8006]),
    ("c.ServeFile(", [8006]),
    ("c.FileAttachment(", [8006]),
    ("c.Redirect(", [8013]),
    ("c.JSONP(", [8008]),
    ("c.String(", [8003, 8008]),
    ("c.JSON(", [8003, 8008]),
    ("c.XML(", [8003, 8008]),
    ("c.YAML(", [8003, 8008]),
    ("c.Data(", [8003, 8008]),
    ("c.Writer.Write(", [8003, 8008]),
    ("c.SaveUploadedFile(", [8004, 8006]),
]

CONTROLLED_SOURCES = [
    'c.Query',
    'c.Param',
    'c.PostForm',
    'c.GetHeader',
    'c.GetCookie',
    'c.ShouldBind',
    'c.ShouldBindJSON',
    'ctx.Query',
    'ctx.Param',
    'ctx.PostForm',
    'ctx.GetHeader',
    'c.DefaultQuery',
    'c.DefaultPostForm',
    'c.ShouldBindQuery',
    'c.ShouldBindXML',
    'c.ShouldBindYAML',
    'c.ClientIP',
]
