# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Spring Boot'
DEPENDENCIES = {'pom': ['spring-boot-starter-web']}


def detect(project_dir, language='java'):
    """检测是否为 Spring Boot 项目"""
    resources = os.path.join(project_dir, 'src', 'main', 'resources')
    return (os.path.isfile(os.path.join(resources, 'application.properties'))
            or os.path.isfile(os.path.join(resources, 'application.yml')))


FILTER_FUNCTIONS = {}

EXTRA_SINKS = [
    ("jdbcTemplate.query(", [6001]),
    ("jdbcTemplate.update(", [6001]),
    ("jdbcTemplate.execute(", [6001]),
    ("restTemplate.getForObject(", [6006]),
    ("restTemplate.exchange(", [6006]),
    ("restTemplate.postForObject(", [6006]),
]

CONTROLLED_SOURCES = [
    '@RequestParam',
    '@PathVariable',
    '@RequestBody',
    '@RequestHeader',
    '@CookieValue',
]
