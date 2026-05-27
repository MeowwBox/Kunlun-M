# -*- coding: utf-8 -*-
from utils.api import *


class CVI_7011():
    """
    Python XXE (XML 外部实体注入)
    覆盖: xml.etree.ElementTree, lxml, xmltodict, defusedxml
    """
    def __init__(self):
        self.svid = 7011
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "XXE"
        self.description = "XML解析操作可能存在XXE外部实体注入风险"
        self.level = 7
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"xml\.etree\.ElementTree\.parse|xml\.etree\.ElementTree\.fromstring|ET\.parse|ET\.fromstring|lxml\.etree\.parse|lxml\.etree\.fromstring|etree\.parse|etree\.fromstring|xmltodict\.parse|minidom\.parse|xml\.sax\.parse|xml\.dom\.minidom\.parse"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
