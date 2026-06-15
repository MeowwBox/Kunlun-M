# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Next.js'
DEPENDENCIES = {'package': ['next']}


def detect(project_dir, language='javascript'):
    """检测是否为 Next.js 项目"""
    return os.path.isfile(os.path.join(project_dir, 'next.config.js')) or \
           os.path.isfile(os.path.join(project_dir, 'next.config.mjs'))


FILTER_FUNCTIONS = {}

CONTROLLED_SOURCES = [
    'req.query',
    'req.headers',
    'req.body',
    'req.cookies',
    'context.query',
    'context.params',
    'searchParams',
    'cookies()',
]

EXTRA_SINKS = [
    ("next/redirect(", [3004]),
    ("dangerouslySetInnerHTML", [3100, 3110]),
    ("router.push(", [3109]),
    ("router.replace(", [3109]),
    ("redirect(", [3109]),
    ("fetch(", [3105]),
    ("prisma.$queryRaw(", [3104]),
]
