# screenshots 目录说明

本目录用于存放 iDrug 平台运行截图、页面截图、接口测试截图和课程展示截图，便于在 README、课程文档、PPT 或答辩材料中引用。

## 建议截图内容

- 首页与平台导航截图。
- DTI 预测输入页面截图。
- DTI 预测结果页面截图。
- 多模型预测任务页面截图。
- 个性化药物推荐输入与结果截图。
- 数据浏览、药物查询、蛋白查询、复合物查询页面截图。
- 用户登录、注册、个人中心、历史结果页面截图。
- 关键接口测试或部署运行截图。

## 命名规范

建议使用英文小写和序号命名，方便排序和引用：

```text
01_home.png
02_dti_input.png
03_dti_result.png
04_prediction_models.png
05_recommendation_result.png
06_user_center.png
07_api_test.png
```

## 使用方式

在根目录 `README.md` 或 `docs/` 文档中可以这样引用：

```md
![DTI 预测结果](screenshots/03_dti_result.png)
```

## 提交注意事项

- 推荐提交 `.png`、`.jpg`、`.jpeg` 格式截图。
- 截图中不要暴露真实服务器密码、数据库密码、API Key、Token、个人隐私信息。
- 避免提交过大的原始图片；必要时先压缩后再放入本目录。
- 不建议提交录屏视频，视频材料请放在 `video/` 目录中以链接或脚本形式说明。
