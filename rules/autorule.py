# -*- coding: utf-8 -*-
"""
    ~~~~
    new auto rule base class
    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""
import re


def trim(data):
    result = []
    for i in data:
        if type(i) is tuple:
            for j in i:
                if j:
                    result.append(j.strip())
            continue
        if i:
            result.append(i.strip())
    return result


def check_tuple(t):
    if isinstance(t, tuple):
        if t[0]:
            return t[0]
        for i in t[::-1]:
            if i:
                return i
    return t


class autorule:
    def __init__(self, is_eval_object=False):
        self.svid = 00000
        self.language = "Auto Rule"
        self.author = "LoRexxar/Kunlun-M"
        self.vulnerability = "Auto Rule"
        self.description = "Auto Rule"
        self.status = True
        self.match_mode = "vustomize-match"
        self.match = ""
        self.vul_function = None
        self.is_eval_object = is_eval_object

    def main(self, regex_string):
        sql_sen = check_tuple(regex_string[0])
        if self.language.lower() == 'php':
            reg = r"\$\w+"
        elif self.language.lower() == 'javascript':
            if self.is_eval_object:
                reg = r"(?:\A|\s|\b)(\w+\s*(?==))|((?<=\(|,)[^\(\)|,|'|\"]+)"
            else:
                reg = r"(?<=\(|,|=)[^\(\)|,|'|\"]+"
        else:
            return None
        if re.search(reg, sql_sen, re.I):
            p = re.compile(reg)
            match = p.findall(sql_sen)
            return trim(match)
        return None
