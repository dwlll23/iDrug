# 模型说明

本目录保存 iDrug 平台的模型推理与模型调用相关代码。

## 已保留内容

- `deepdta/`：DeepDTA 推理脚本、工具代码、示例输入和依赖说明。
- `hyperattentionati/`：HyperAttentionDTI 推理脚本、工具代码、示例输入和依赖说明。
- `psichic/`：PSICHIC 推理脚本、模型结构代码、工具代码、示例输入和配置文件。
- `predict.py`：原项目中的 DTI 预测入口代码。
- `integration/`：从后端复制出的模型调度与个性化重排序相关代码，便于课程检查；实际运行以后端 `backend/web/` 中的同名逻辑为准。

## 未上传的模型文件

模型权重文件较大，未上传至 GitHub，可通过部署环境或课程提交压缩包提供。当前整理中已排除：

- `deepdta/checkpoints/gpcr_1_best_finetuned.h5`
- `hyperattentionati/checkpoints/gpcr_unseen_protein.pt`
- `hyperattentionati/checkpoints/human_random.pt`
- `psichic/checkpoints/model.pt`
- `psichic/checkpoints/degree.pt`

运行真实模型推理前，请将对应权重放回各模型的 `checkpoints/` 目录，或在部署环境中配置等价路径。
