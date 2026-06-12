# -*- coding: utf-8 -*-
"""
    JavaScript base config (standard library)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Node.js 标准库修复函数和可控输入源配置（基础配置，非框架配置）

    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

IS_REPAIR = {
    # XSS 防护
    "DOMPurify.sanitize": [3100, 3103, 3107],
    "sanitize-html": [3100, 3103, 3107],
    "escape-html": [3100, 3103, 3107],
    "he.encode": [3100, 3103, 3107],
    "xss": [3100, 3103, 3107],
    "bleach.sanitize": [3100, 3103],
    "insane": [3100, 3103],
    "jsesc": [3100, 3103],
    "serialize-javascript": [3103, 3107],

    # SQL 注入防护
    "mysql.escape": [3104],
    "mysql.escapeId": [3104],
    "mysql2.escape": [3104],
    "mysql2.escapeId": [3104],
    "pg.escapeLiteral": [3104],
    "pg.escapeIdentifier": [3104],
    "sequelize.escape": [3104],
    "format": [3104],
    "parseInt": [3104],
    "Number": [3104],

    # 命令注入防护
    "shell-escape": [3100],
    "shell-escape-quote": [3100],
    "shellwords.escape": [3100],
    "execFile": [3100],
    "execFileSync": [3100],
    "parseInt": [3100],

    # 路径穿越防护
    "path.normalize": [3101],
    "path.resolve": [3101],
    "path.basename": [3101],
    "path.dirname": [3101],
    "sanitize-filename": [3101],

    # SSRF 防护
    "URL": [3102],
    "url.URL": [3102],
    "dns.lookup": [3102],
    "URL.parse": [3102],

    # 编码/加密
    "encodeURIComponent": [3100, 3102, 3106],
    "encodeURI": [3100, 3102, 3106],
    "crypto.createHash": [3100, 3103],
    "Buffer.from": [3100],

    # 反序列化防护
    "JSON.parse": [3105],
    "JSON.stringify": [3105],

    # 开放重定向防护
    "URL.parse": [3106],
    "url.parse": [3106],
    "URL.URL": [3106],
    "startsWith": [3106],

    # XXE 防护 (3107)
    "DOMParser": [3107],
    "libxmljs.parseXml": [3107],
    "xml2js.parseString": [3107],

    # ReDoS 防护 (3108)
    "RegExp.escape": [3108],  # 提案 API
    "escapeRegExp": [3108],  # lodash/underscore
    "XRegExp.escape": [3108],
    "safe-regex": [3108],

    # 框架内置防护
    "express.json": [3100],
    "express.urlencoded": [3100],
    "helmet": [3100, 3103],
    "csurf": [3100],
    "cors": [3102],
    "body-parser": [3100],
    "express-validator": [3100, 3101, 3104],
    "joi": [3100, 3101, 3104, 3108],
    "zod": [3100, 3101, 3104, 3108],
    "class-validator": [3100, 3101, 3104],
    "ValidationPipe": [3100, 3101, 3104],
}

IS_CONTROLLED = [
    # Express/Connect
    "req.query",
    "req.body",
    "req.params",
    "req.headers",
    "req.cookies",
    "req.files",
    "req.url",
    "req.method",
    "req.path",
    "req.host",
    "req.ip",
    "req.ips",
    "req.fresh",
    "req.stale",
    "req.xhr",
    "req.protocol",
    "req.secure",
    "req.acceptedLanguages",
    "req.acceptedCharsets",
    "req.accepts",
    "req.get",
    "req.param",
    # Koa
    "ctx.query",
    "ctx.params",
    "ctx.request.body",
    "ctx.request.query",
    "ctx.request.header",
    "ctx.request.headers",
    "ctx.ip",
    "ctx.ips",
    "ctx.host",
    "ctx.protocol",
    "ctx.url",
    "ctx.path",
    "ctx.method",
    # Hapi
    "request.query",
    "request.params",
    "request.payload",
    "request.headers",
    "request.info",
    # Fastify
    "request.query",
    "request.body",
    "request.params",
    "request.headers",
    # process
    "process.env",
    "process.argv",
    # 原生 http
    "req.url",
    "req.method",
    "req.headers",
]
