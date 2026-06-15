# -*- coding: utf-8 -*-
"""
    Go base config (standard library)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Go 修复函数和可控输入源配置（基础配置，非框架配置）

    CVI 编号对照：
    - 8001: 命令注入
    - 8002: SQL注入
    - 8003: XSS (反射型)
    - 8004: 文件操作
    - 8005: SSRF
    - 8006: 路径穿越
    - 8007: 不安全反序列化
    - 8008: XSS (存储型)

    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved.
"""

# 修复函数 → 可防御的 CVI 编号
IS_REPAIR = {
    # ---- XSS 防御 (8003, 8008) ----
    "html.EscapeString": [8003, 8008],
    "html.Escape": [8003, 8008],
    "template.HTMLEscapeString": [8003, 8008],
    "template.JSEscapeString": [8003, 8008],
    "template.HTML": [8003, 8008],
    "json.Marshal": [8003, 8008],
    "json.MarshalIndent": [8003, 8008],
    "json.HTMLEscape": [8003, 8008],
    "bluemonday.StrictPolicy.Sanitize": [8003, 8008],
    "bluemonday.UGCPolicy.Sanitize": [8003, 8008],
    "bluemonday.Sanitize": [8003, 8008],
    "sanitizer.Sanitize": [8003, 8008],

    # ---- 命令注入防御 (8001) ----
    "shellescape.Quote": [8001],
    "strconv.Quote": [8001],

    # ---- SQL 注入防御 (8002) ----
    "db.Query": [8002],
    "db.QueryRow": [8002],
    "db.Exec": [8002],
    "db.Prepare": [8002],
    "tx.Exec": [8002],
    "tx.Query": [8002],
    "tx.QueryRow": [8002],
    "tx.Prepare": [8002],
    "sqlx.Query": [8002],
    "sqlx.Queryx": [8002],
    "sqlx.Exec": [8002],
    "sqlx.Get": [8002],
    "sqlx.Select": [8002],
    "sqlx.NamedExec": [8002],
    "gorm.DB.Where": [8002],
    "gorm.DB.Raw": [8002],
    "gorm.DB.Exec": [8002],
    "gorm.DB.First": [8002],
    "gorm.DB.Find": [8002],
    "gorm.DB.Take": [8002],

    # ---- 文件操作防御 (8004) / 路径穿越防御 (8006) ----
    "filepath.Base": [8004, 8006],
    "filepath.Dir": [8004, 8006],
    "filepath.Clean": [8004, 8006],
    "path.Base": [8004, 8006],
    "path.Clean": [8004, 8006],
    "url.Parse": [8005, 8006],

    # ---- SSRF 防御 (8005) ----
    "url.Parse": [8005],
    "neturl.Parse": [8005],

    # ---- 反序列化防御 (8007) ----
    "json.Unmarshal": [8007],
    "json.NewDecoder": [8007],
    "encoding/gob.NewDecoder": [8007],

    # ---- 通用类型转换（多漏洞防御）----
    "strconv.Atoi": [8001, 8002, 8005],
    "strconv.ParseInt": [8001, 8002, 8005],
    "strconv.ParseUint": [8001, 8002, 8005],
    "strconv.ParseFloat": [8001, 8002, 8005],
    "strconv.Itoa": [8001, 8002, 8005],
    "strconv.FormatInt": [8001, 8002, 8005],
    "regexp.QuoteMeta": [8001, 8002, 8005],
    "url.QueryEscape": [8001, 8002, 8005, 8006],
    "url.PathEscape": [8001, 8005, 8006],
}

# 可控输入源
IS_CONTROLLED = [
    # net/http - http.Request
    "r.URL.Query()",
    "r.FormValue",
    "r.PostFormValue",
    "r.Header.Get",
    "r.Body",
    "r.URL.Path",
    "r.URL.RawPath",
    "r.Host",
    "r.RemoteAddr",
    "r.UserAgent",
    "r.Referer",
    "r.Method",
    "r.URL.RawQuery",
    "r.URL.Fragment",
    "r.URL.Host",
    "r.URL.Scheme",
    "r.Cookies",
    "r.Cookie",
    "r.Context",
    "r.Form",
    "r.PostForm",
    "r.MultipartForm",
    "r.TransferEncoding",
    "request.FormValue",
    "request.PostFormValue",
    "request.URL.Query",
    "request.URL.Path",
    "request.Header",
    "request.Body",
    "request.Host",
    "request.UserAgent",
    "request.Referer",
    "request.Cookies",
    "request.Cookie",
    # os
    "os.Args",
    "os.Getenv",
    "os.Stdin",
    # flag
    "flag.String",
    "flag.Int",
    "flag.Bool",
    "flag.Float64",
    # Gin framework
    "c.Query",
    "c.DefaultQuery",
    "c.Param",
    "c.PostForm",
    "c.DefaultPostForm",
    "c.GetHeader",
    "c.GetCookie",
    "c.ShouldBind",
    "c.ShouldBindJSON",
    "c.ShouldBindQuery",
    "c.ShouldBindUri",
    "c.ShouldBindHeader",
    "c.ShouldBindWith",
    "c.BindJSON",
    "c.BindQuery",
    "c.BindUri",
    "c.BindHeader",
    "c.Request.URL",
    "c.Request.Header",
    "c.Request.Body",
    "c.Request.FormValue",
    "ctx.Query",
    "ctx.DefaultQuery",
    "ctx.Param",
    "ctx.PostForm",
    "ctx.GetHeader",
    "ctx.GetCookie",
    # Echo framework
    "echo.QueryParams",
    "echo.FormValue",
    "echo.QueryParam",
    "echo.PathParam",
    "echo.FormParams",
    "echo.Cookies",
    "echo.Cookie",
    "echo.Header",
    "echo.Context.QueryParam",
    "echo.Context.Param",
    "echo.Context.FormValue",
    "echo.Context.FormParams",
    "echo.Context.Cookie",
    "echo.Context.Cookies",
    "echo.Context.GetHeader",
    # Fiber framework
    "fiber.Query",
    "fiber.Params",
    "fiber.Body",
    "fiber.Get",
    "fiber.Cookies",
    "fiber.Locals",
    # Beego framework
    "beego.Input",
    "beego.GetString",
    "beego.GetStrings",
    "beego.Ctx.Input.Query",
    "beego.Ctx.Input.Param",
    "beego.Ctx.Input.Header",
    "beego.Ctx.Input.Cookie",
    "beego.Ctx.Input.RequestBody",
    # Chi router
    "chi.URLParam",
    "chi.RouteContext",
    # Gorilla/mux
    "mux.Vars",
    # io/ioutil
    "ioutil.ReadAll",
    "io.ReadAll",
    # Context
    "context.Value",
    "ctx.Value",
]
