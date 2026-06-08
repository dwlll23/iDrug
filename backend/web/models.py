from django.db import models


class DiseaseRecommendation(models.Model):
    cid = models.CharField(max_length=20, default='N/A', verbose_name='PubChem CID')
    # 新增分子信息字段
    molecular_formula = models.CharField(max_length=100, default='N/A', verbose_name='分子式')
    molecular_weight = models.CharField(max_length=20, default='N/A', verbose_name='分子量')
    smiles = models.TextField(default='N/A', verbose_name='SMILES字符串')
    disease_type = models.CharField(max_length=200, verbose_name="疾病类型")
    age_min = models.IntegerField(null=True, blank=True, verbose_name="年龄下限")
    age_max = models.IntegerField(null=True, blank=True, verbose_name="年龄上限")
    gender = models.CharField(
        max_length=10,
        choices=[('男', '男'), ('女', '女'), ('不限', '不限')],
        default='不限',
        verbose_name="性别"
    )

    drug_name = models.CharField(max_length=200, verbose_name="药物名称")
    priority = models.IntegerField(default=10, verbose_name="优先级（越小越优先）")
    reason = models.TextField(blank=True, verbose_name="推荐理由")

    price_ref = models.CharField(max_length=50, blank=True, verbose_name="参考价格")
    medicare_cn = models.CharField(max_length=50, blank=True, verbose_name="医保覆盖")
    usage_summary = models.TextField(blank=True, verbose_name="使用说明摘要")

    def __str__(self):
        return f"{self.disease_type} - {self.drug_name}"

    class Meta:

        db_table = 'web_diseaserecommendation'  # 确保表名一致
        verbose_name = "疾病推荐药物"
        verbose_name_plural = "疾病推荐药物"