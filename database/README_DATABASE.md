# 数据库说明

## 数据库类型

当前项目使用 MySQL，Django 配置文件位于：

```text
backend/iDrug/settings.py
```

真实数据库密码未提交到 GitHub。请通过环境变量配置：

```text
MYSQL_DATABASE=DrugX
MYSQL_USER=your_database_user
MYSQL_PASSWORD=your_database_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
```

## 主要数据表

- `user`：平台用户表，来源于 `backend/web/ms.py`。
- `pdb_url`：PDB ID 与结构资源 URL 映射表，来源于 `backend/web/ms.py`。
- `web_diseaserecommendation`：疾病场景下的推荐药物、适用条件和说明信息，来源于 `backend/web/models.py`。
- Django 内置表：`auth_*`、`django_session`、`django_admin_log` 等，由 Django migrations 创建。

## 初始化方式

1. 在 MySQL 中创建数据库，例如 `DrugX`。
2. 配置上述环境变量。
3. 进入后端目录执行：

```bash
cd backend
python manage.py migrate
```

当前源项目未发现独立 `.sql` 文件，因此本目录保留 Django migrations 副本用于表结构追踪。
