# Kunlun-M 扫描报告（模板）

## 元信息

- target: {{meta.target}}
- task_id: {{meta.task_id}}
- project_id: {{meta.project_id}}
- started_at: {{meta.started_at}}
- finished_at: {{meta.finished_at}}
- settings_module: {{meta.settings_module}}

## 汇总

- total: {{summary.total}}
- max_severity: {{summary.max_severity}}
- by_severity: {{summary.by_severity}}

## 发现项（Top N）

| severity | cvi_id | rule_name | language | file | is_unconfirm |
| --- | --- | --- | --- | --- | --- |
{{#each vulnerabilities}}
| {{severity}} | {{cvi_id}} | {{rule_name}} | {{language}} | {{file}} | {{is_unconfirm}} |
{{/each}}

## 退出码

- code: {{exit.code}}
- reason: {{exit.reason}}

