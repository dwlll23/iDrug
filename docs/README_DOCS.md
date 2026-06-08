# docs 目录说明

本目录用于存放软件开发课程大作业相关文档材料，包括需求分析、概要设计、详细设计、测试用例、部署说明、使用说明以及阶段性章节初稿。

## 建议内容

- `requirements.md`：需求分析、用户角色、功能需求与非功能需求。
- `design.md`：系统架构、模块划分、接口设计、数据流说明。
- `database_design.md`：数据库设计、主要数据表、字段含义和关系说明。
- `test_cases.md`：功能测试、接口测试、异常场景测试和结果记录。
- `user_manual.md`：平台使用说明、主要页面流程、输入输出示例。
- `deployment.md`：部署环境、依赖安装、环境变量和启动方式。
- `figures/`：系统架构图、用例图、时序图、ER 图、流程图等图片资源。

## figures 子目录

`figures/` 用于集中保存文档中引用的图片。建议使用清晰、稳定的文件名，例如：

```text
architecture.png
use_case_diagram.png
sequence_prediction.png
er_diagram.png
workflow_recommendation.png
```

在 Markdown 文档中引用图片时，建议使用相对路径：

```md
![系统架构图](figures/architecture.png)
```

## 提交注意事项

- 建议提交 Markdown、PNG、JPG、SVG 等便于 GitHub 查看和版本管理的文件。
- 不建议提交 Word、PDF、压缩包等二进制文档；如课程要求提交正式版，可在课程平台或压缩包中单独提供。
- 文档中不要写入真实数据库密码、服务器账号、API Key、Token 等敏感信息。
- 如果某份材料尚未完成，可以先提交章节初稿，并在文档开头标明“待完善”。
