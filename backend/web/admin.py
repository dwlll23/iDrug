from django.contrib import admin

from .models import DiseaseRecommendation  # 导入您的模型

# 注册模型到后台
admin.site.register(DiseaseRecommendation)
