# -*- coding: utf-8 -*-
import json
import os

FRAMEWORK_NAME = 'Express'
DEPENDENCIES = {'package': ['express']}


def detect(project_dir, language='javascript'):
    """检测是否为 Express 项目"""
    pkg_path = os.path.join(project_dir, 'package.json')
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                return 'express' in deps
        except (json.JSONDecodeError, IOError):
            pass
    return False


FILTER_FUNCTIONS = {
    'express-validator': [3100, 3101, 3102, 3104],
}

EXTRA_SINKS = [
    ("res.render(", [3005]),
    ("res.redirect(", [3004]),
    ("res.json(", [3100, 3110]),
    ("res.send(", [3100, 3110]),
    ("res.sendFile(", [3102, 3106]),
    ("res.download(", [3102, 3106]),
    ("child_process.exec(", [3101]),
    ("child_process.spawn(", [3101]),
    ("child_process.execSync(", [3101]),
    ("fs.readFile(", [3102, 3106]),
    ("fs.writeFile(", [3102]),
    ("fs.readFileSync(", [3102, 3106]),
    ("fetch(", [3105]),
    ("axios.get(", [3105]),
    ("axios.post(", [3105]),
    ("eval(", [3103]),
    ("new Function(", [3103]),
]

CONTROLLED_SOURCES = [
    'req.query',
    'req.body',
    'req.params',
    'req.headers',
    'req.cookies',
    'req.files',
    'req.url',
    'req.method',
    'req.ip',
    'req.get',
    'req.param',
    'req.signedCookies',
    'req.hostname',
    'req.originalUrl',
    'req.subdomains',
    'req.user',
]
