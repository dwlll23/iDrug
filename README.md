# iDrug——多场景 DTI 预测与个性化药物推荐辅助平台

## 项目简介

iDrug 是一个面向药物-靶点相互作用（DTI）预测与个性化药物推荐的课程项目。平台基于 Django 提供后端接口和页面路由，前端采用 Django 页面文件、静态 CSS 和图片资源，模型层集成 HyperAttentionDTI、PSICHIC、DeepDTA 等推理代码，用于多场景预测、结构查询和个性化重排序展示。

在线部署地址：http://106.54.24.49/

## 目录结构

```text
iDrug-Software-Development-Course/
├── backend/              Django 后端代码、业务逻辑、运行脚本和小型数据缓存
├── frontend/             Django 页面文件、CSS、图片等前端页面资源
├── model/                DTI 模型推理代码、模型调用说明和权重占位说明
├── database/             Django migrations 与数据库初始化说明
├── need_review/          暂无未分类代码，仅保留说明
├── README.md
└── .gitignore
```

## 后端运行说明

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DJANGO_SECRET_KEY=your_secret_key
set MYSQL_DATABASE=DrugX
set MYSQL_USER=your_database_user
set MYSQL_PASSWORD=your_database_password
set MYSQL_HOST=localhost
set MYSQL_PORT=3306
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Windows 下也可以执行 `backend/start_backend.bat` 启动开发服务器。首次运行前请先创建 MySQL 数据库并配置环境变量。

## 前端运行说明

本项目当前前端不是独立的 Vue/React/Vite 工程，而是由 Django 页面文件和静态资源组成。启动后端后，访问：

```text
http://127.0.0.1:8000/
```

前端资源位于 `frontend/pages/` 和 `frontend/static/`，Django 配置已指向这两个目录。

## 模型文件说明

模型代码位于 `model/`。由于模型权重文件较大，未上传至 GitHub。

后端中的 `backend/web/prediction_model_services.py` 会从仓库根目录下的 `model/` 读取推理脚本和模型目录。运行真实预测前，请按 `model/README_MODEL.md` 补齐对应 checkpoints 文件。

## 数据库说明

项目使用 MySQL。数据库连接配置位于 `backend/iDrug/settings.py`，真实用户名和密码不提交到仓库，改由环境变量或占位符配置。数据库表结构可通过 `database/migrations/` 或 `backend/web/migrations/` 初始化。
