import codecs
import numpy as np
import pandas as pd
import torch
from subword_nmt.apply_bpe import BPE
from torch.utils import data
import os
import traceback

# =================== 核心配置（适配Django项目路径） ===================
# 获取当前文件所在目录（predict.py）
PREDICT_DIR = os.path.dirname(os.path.abspath(__file__))
# ESPF目录绝对路径（避免相对路径错误）
ESPF_DIR = os.path.join(PREDICT_DIR, 'ESPF')
# 模型文件绝对路径
MODEL_PATH = os.path.join(PREDICT_DIR, 'model.pth')

# =================== 全局初始化（只加载一次，提升性能） ===================
# 初始化Protein BPE编码器
try:
    vocab_path = os.path.join(ESPF_DIR, 'protein_codes_uniprot.txt')
    bpe_codes_protein = codecs.open(vocab_path, 'r', encoding='utf-8')
    pbpe = BPE(bpe_codes_protein, merges=-1, separator='')
    sub_csv = pd.read_csv(os.path.join(ESPF_DIR, 'subword_units_map_uniprot.csv'))
    idx2word_p = sub_csv['index'].values
    words2idx_p = dict(zip(idx2word_p, range(0, len(idx2word_p))))
except Exception as e:
    print(f"Protein编码器初始化失败: {str(e)}")
    traceback.print_exc()
    pbpe = None
    words2idx_p = {}

# 初始化Drug BPE编码器
try:
    vocab_path = os.path.join(ESPF_DIR, 'drug_codes_chembl.txt')
    bpe_codes_drug = codecs.open(vocab_path, 'r', encoding='utf-8')
    dbpe = BPE(bpe_codes_drug, merges=-1, separator='')
    sub_csv = pd.read_csv(os.path.join(ESPF_DIR, 'subword_units_map_chembl.csv'))
    idx2word_d = sub_csv['index'].values
    words2idx_d = dict(zip(idx2word_d, range(0, len(idx2word_d))))
except Exception as e:
    print(f"Drug编码器初始化失败: {str(e)}")
    traceback.print_exc()
    dbpe = None
    words2idx_d = {}

# 初始化模型（全局加载，避免重复加载）
model = None
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

try:
    # 加载模型（兼容CPU/GPU）
    if os.path.exists(MODEL_PATH):
        model = torch.load(MODEL_PATH, map_location=device)
        model.eval()  # 设置为评估模式
        print(f"模型加载成功: {MODEL_PATH}")
    else:
        print(f"模型文件不存在: {MODEL_PATH}")
except Exception as e:
    print(f"模型加载失败: {str(e)}")
    traceback.print_exc()
    model = None


def drug2emb_encoder(x):
    """
    药物SMILES字符串转嵌入编码
    :param x: SMILES字符串
    :return: 编码后的数组 + mask数组
    """
    max_d = 50
    if not dbpe or not words2idx_d:
        return np.zeros(max_d), np.zeros(max_d)

    try:
        t1 = dbpe.process_line(x).split()  # BPE分词
        i1 = np.asarray([words2idx_d.get(i, 0) for i in t1])  # 避免KeyError
    except Exception as e:
        print(f"Drug编码错误: {str(e)}, SMILES: {x[:50]}")
        i1 = np.array([0])

    l = len(i1)
    # 填充/截断到固定长度
    if l < max_d:
        i = np.pad(i1, (0, max_d - l), 'constant', constant_values=0)
        input_mask = ([1] * l) + ([0] * (max_d - l))
    else:
        i = i1[:max_d]
        input_mask = [1] * max_d

    return i, np.asarray(input_mask)


def protein2emb_encoder(x):
    """
    蛋白质序列转嵌入编码
    :param x: 蛋白质序列字符串
    :return: 编码后的数组 + mask数组
    """
    max_p = 545
    if not pbpe or not words2idx_p:
        return np.zeros(max_p), np.zeros(max_p)

    try:
        t1 = pbpe.process_line(x).split()  # BPE分词
        i1 = np.asarray([words2idx_p.get(i, 0) for i in t1])  # 避免KeyError
    except Exception as e:
        print(f"Protein编码错误: {str(e)}, 序列长度: {len(x)}")
        i1 = np.array([0])

    l = len(i1)
    # 填充/截断到固定长度
    if l < max_p:
        i = np.pad(i1, (0, max_p - l), 'constant', constant_values=0)
        input_mask = ([1] * l) + ([0] * (max_p - l))
    else:
        i = i1[:max_p]
        input_mask = [1] * max_p

    return i, np.asarray(input_mask)


def predict_dti(inputdrug, intputprotein):
    """
    预测药物-靶点相互作用概率
    :param inputdrug: 药物SMILES字符串
    :param intputprotein: 蛋白质序列字符串
    :return: 预测概率值（0-1之间），失败返回0.0
    """
    # 输入验证
    if not inputdrug or not intputprotein:
        print("输入为空：drug={}, protein={}".format(inputdrug[:20] if inputdrug else "",
                                                    intputprotein[:20] if intputprotein else ""))
        return 0.0

    # 检查模型是否加载成功
    if model is None:
        print("模型未加载，无法预测")
        return 0.0

    try:
        # 编码药物和蛋白质
        d_v, input_mask_d = drug2emb_encoder(inputdrug)
        p_v, input_mask_p = protein2emb_encoder(intputprotein)

        # 转换为tensor并调整维度
        d_v = torch.tensor(np.array([d_v]), dtype=torch.long).to(device)
        input_mask_d = torch.tensor(np.array([input_mask_d]), dtype=torch.long).to(device)
        p_v = torch.tensor(np.array([p_v]), dtype=torch.long).to(device)
        input_mask_p = torch.tensor(np.array([input_mask_p]), dtype=torch.long).to(device)

        # 模型预测（禁用梯度计算，提升速度）
        with torch.no_grad():
            score = model(d_v, p_v, input_mask_d, input_mask_p)
            m = torch.nn.Sigmoid()
            logits = torch.squeeze(m(score))
            logits = logits.cpu().numpy()  # 统一转到CPU
            y_pred = logits.flatten().tolist()
            y_max = max(y_pred) if y_pred else 0.0

        # 确保返回值在0-1之间
        y_max = max(0.0, min(1.0, y_max))
        return y_max

    except Exception as e:
        print(f"DTI预测错误: {str(e)}")
        traceback.print_exc()
        return 0.0


# =================== 测试函数（可选） ===================
if __name__ == "__main__":
    # 测试用例
    test_drug = 'CN(C)CC1CCN2C=C(C3=CC=CC=C32)C4=C(C5=CN(CCO1)C6=CC=CC=C65)C(=O)NC4=O'
    test_protein = 'PFWKILNPLLERGTYYYFMGQQPGKVLGDQRRPSLPALHFIKGAGKKESSRHGGPHCNVFVEHEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTVYGVSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGSGFRSPHLWKKSSTLTSSRLATGEEEGGGSSSKRFLRSCSASCVPHGAKDTEWRSVTLPRDLQSTGRQFDSSTFGGHKSEKPALPRKRAGENRSDQVTRGTVTPPPRLVKKNEEAADEVFKDIMESSPGSSPPNLTPKPLRRQVTVAPASGLPHKEEAGKGSALGTPAAAEPVTPTSKAGSGAPGGTSKGPAEESRVRRHKHSSESPGRDKGKLSRLKPAPPPPPAASAGKAGGKPSQSPSQEAAGEAVLGAKTKATSLVDAVNSDAAKPSQPGEGLKKPVLPATPKPQSAKPSGTPISPAPVPSTLPSASSALAGDQPSSTAFIPLISTRVSLRKTRQPPERIASGAITKGVVLDSTEALCLAISRNSEQMASHSAVLEAGKNLYTFCVSYVDSIQQMRNKFAFREAINKLENNLRELQICPATAGSGPAATQDFSKLLSSVKEISDIVQR'

    result = predict_dti(test_drug, test_protein)
    print(f"预测概率: {result:.4f}")