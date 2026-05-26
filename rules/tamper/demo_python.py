# -*- coding: utf-8 -*-
"""
    demo_python
    ~~~~~~~~~~~
    Python 修复函数和可控输入源配置
    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""
PYTHON_IS_REPAIR_DEFAULT = {
    "html.escape": [2000, 2006],
    "markupsafe.escape": [2000, 2006],
    "shlex.quote": [2000, 2001],
    "escape": [2000, 2006],
    "int": [2000, 2001],
    "str": [2000],
    "json.dumps": [2006],
    "parameterized": [2002],
    "execute": [2002],
    "safe_load": [2003],
}

PYTHON_IS_CONTROLLED_DEFAULT = [
    "request.args",
    "request.form",
    "request.data",
    "request.json",
    "request.files",
    "request.values",
    "request.headers",
    "sys.argv",
    "input()",
    "os.environ",
    "flask.request",
    "environ.get",
    "environ",
    "GET",
    "POST",
    "self.request.get_argument",
]
