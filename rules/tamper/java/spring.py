# -*- coding: utf-8 -*-
import os

FRAMEWORK_NAME = 'Spring Boot'
DEPENDENCIES = {'pom': ['spring-boot-starter-web']}


def detect(project_dir, language='java'):
    """检测是否为 Spring Boot 项目"""
    resources = os.path.join(project_dir, 'src', 'main', 'resources')
    return (os.path.isfile(os.path.join(resources, 'application.properties'))
            or os.path.isfile(os.path.join(resources, 'application.yml')))


FILTER_FUNCTIONS = {
    # Validation annotation - validated input is safer for these CVIs
    '@Valid': [6002, 6004, 6043],
}

EXTRA_SINKS = [
    ("jdbcTemplate.query(", [6001]),
    ("jdbcTemplate.update(", [6001]),
    ("jdbcTemplate.execute(", [6001]),
    ("restTemplate.getForObject(", [6006]),
    ("restTemplate.exchange(", [6006]),
    ("restTemplate.postForObject(", [6006]),
    # Spring MVC view-related XSS sinks
    ("ModelAndView", [6002]),
    ("addAttribute(", [6002]),
    # Open redirect sinks
    ("sendRedirect(", [6015]),
    ("RedirectView", [6015]),
    # Additional JDBC / ORM SQL injection sinks
    ("JdbcTemplate.queryForRowSet(", [6001]),
    ("JdbcTemplate.batchUpdate(", [6001]),
    ("EntityManager.createNativeQuery(", [6001]),
    # JPA / JPQL annotation-based query sink
    ("@Query", [6048]),
    # Spring Expression Language injection
    ("SpEL", [6012]),
    # Command execution sinks
    ("Runtime.exec(", [6003]),
    ("ProcessBuilder", [6003]),
    # XStream deserialization
    ("XStream", [6044]),
    ("XStream.fromXML(", [6044]),
]

CONTROLLED_SOURCES = [
    '@RequestParam',
    '@PathVariable',
    '@RequestBody',
    '@RequestHeader',
    '@CookieValue',
    # Additional Spring-controlled parameter bindings
    '@ModelAttribute',
    '@SessionAttributes',
    '@RequestPart',
    '@MatrixVariable',
    '@AuthenticationPrincipal',
    # Servlet API objects (request/response/session)
    'HttpServletRequest',
    'HttpServletResponse',
    'HttpSession',
    'Principal',
    # Multipart upload source
    'MultipartFile',
]
