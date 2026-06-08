# import pypdb
#
# from pypdb.clients.pdb.pdb_client import get_pdb_file
# from Bio.PDB import PDBParser
# from Bio import PDB
# from io import StringIO
#
# pdb_id = '1SHA' # 鐢ㄦ偍鎯虫煡璇㈢殑 PDB ID 鏇挎崲
# description = pypdb.describe_pdb(pdb_id)
#
# print(description.keys())

# source = ""
# if 'diffrn_source' in description:
#     source = "NOT FOUND"
# else:
#     ssource = description.get('diffrn_source')
#     if 'source' in ssource:
#         source = ssource.get('source')
#     else:
#         source = "NOT FOUND"
# print(source)

# # print(type(description['diffrn_source'][0]['source']))
#
# # print(description['diffrn_source'][0]['source'])
#
# pdb_file = get_pdb_file(pdb_id)
# parser = PDBParser()
# structure = parser.get_structure(pdb_id, StringIO(pdb_file))
# ppb = PDB.PPBuilder()
# seq = ppb.build_peptides(structure)[0].get_sequence()
# print(pdb_id, seq)
#
# ssource = description.get('diffrn_source')[0]
# source = ""
# if 'source' in ssource:
#     source = ssource.get('source')
# else:
#     source = "NOT FOUND"
# print(source)
#
# exptl = description.get('exptl')[0]
# method = ""
# if 'method' in exptl:
#     method = exptl.get('method')
# else:
#     method = "NOT FOUND"
#
# print(method)
#
#
# ac_info = description.get('rcsb_accession_info')
# deposit_date = ""
# release_date = ""
# if 'deposit_date' in ac_info:
#     deposit_date = ac_info.get('deposit_date')
# else:
#     deposit_date = "NOT FOUND"
# if 'initial_release_date' in ac_info:
#     release_date = ac_info.get('initial_release_date')
# else:
#     release_date = "NOT FOUND"
# print(deposit_date, release_date)
#
# entry_info = description.get('rcsb_entry_info')
# molecular_weight = ""
# nonpolymer_bound_components = ""
# if 'molecular_weight' in entry_info:
#     molecular_weight = entry_info.get('molecular_weight')
# else:
#     molecular_weight = "NOT FOUND"
# if 'nonpolymer_bound_components' in entry_info:
#     nonpolymer_bound_components = entry_info.get('nonpolymer_bound_components')
# else:
#     nonpolymer_bound_components = "NOT FOUND"
# print(molecular_weight, nonpolymer_bound_components)
#
# struct_keywords = description.get('struct_keywords')
# pdbx_keywords = ""
# if 'pdbx_keywords' in struct_keywords:
#     pdbx_keywords = struct_keywords.get('pdbx_keywords')
# else:
#     pdbx_keywords = 'NOT FOUND'
# print(pdbx_keywords)
#
#
# sequence = 'MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIPFIETSAKTRQRVEDAFYTLVREIRQHKLRKLNPPDESGPG'  # 鐢ㄦ偍鎯虫煡璇㈢殑铔嬬櫧璐ㄥ簭鍒楁浛鎹?
# q = pypdb.Query(sequence,
#           query_type="sequence",
#           return_type="polymer_entity")
# q_s = q.search()
# pdb_id2 = q_s['result_set'][0]['identifier']
# print(pdb_id2)
#
# q2 = pypdb.Query(sequence,
#           query_type="sequence")
# pdb_ids = q2.search()
# print(pdb_ids[0])
#
#
#
#
#



#
#
# import function
# from chemspipy import ChemSpider
# import pubchempy as pcp
# cs = ChemSpider('GJjrQLtK80AczVd34CTS0GSh4fNAOkVQ')
# SMILES = "CN(C)CC1CCN2C=C(C3=CC=CC=C32)C4=C(C5=CN(CCO1)C6=CC=CC=C65)C(=O)NC4=O"
# c = pcp.get_compounds(SMILES, 'smiles')[0]
# compound = cs.get_compound(c.cid)
# data = function.get_drug_info(compound , c)
# print(data)
#
# from pymol import cmd
#
# cmd.fetch('5IMT') # 鑾峰彇 PDB 鏂囦欢
# cmd.show_as('cartoon') # 璁剧疆鏄剧ず妯″紡涓哄崱閫?
# cmd.bg_color('white') # 灏嗚儗鏅鑹蹭慨鏀逛负鐧借壊
# cmd.set('ray_opaque_background', 1) # 绂佺敤閫忔槑鑳屾櫙
# cmd.png('protein.png', width=800, height=600, dpi=300) # 娓叉煋骞朵繚瀛樺垎瀛愮殑 2D 鍥惧儚


# import requests
#
# # ImageKit.io API瀵嗛挜鍜岀閽?
# api_key = 'your_api_key'
# api_secret = 'your_api_secret'
# url_endpoints = 'https://ik.imagekit.io/HeeKaai/DrugX/'
#
# # 鍥剧墖鏂囦欢璺緞
# image_file_path = "D:\Hee\pycharmproject\DrugX\pic\kai.JPG"
#
# # 涓婁紶鍥剧墖
# response = requests.post(
#     url_endpoints,
#     auth=(api_key, api_secret),
#     files={'file': open(image_file_path, 'rb')},
#     verify=False
# )
#
# # 鎵撳嵃鏈嶅姟鍣ㄨ繑鍥炵殑鏁版嵁
# print('Response:', response.text)
#
# # 鑾峰彇杩斿洖鐨凧SON鏁版嵁
# data = response.json()
#
# # 鑾峰彇鍥剧墖鐨刄RL閾炬帴
# image_url = data['url']
#
# print('Image URL:', image_url)


# pdb_id = input()
#
# from cloudinary.uploader import upload
# import cloudinary
# from pymol import cmd
#
# fetch_path = r'D:\Hee\pycharmproject\DrugX\pic'
# pic_path = fetch_path + fr'\{pdb_id}'
#
# cmd.set('fetch_path', fetch_path)
#
# cmd.fetch(pdb_id) # 鑾峰彇 PDB 鏂囦欢
# cmd.show_as('cartoon') # 璁剧疆鏄剧ず妯″紡涓哄崱閫?
# cmd.bg_color('white') # 灏嗚儗鏅鑹蹭慨鏀逛负鐧借壊
# cmd.set('ray_opaque_background', 1) # 绂佺敤閫忔槑鑳屾櫙
# cmd.png(pic_path, width=500, height=500, dpi=300) # 娓叉煋骞朵繚瀛樺垎瀛愮殑 2D 鍥惧儚


# cloudinary.config(
#   cloud_name = "dutuzuhwu",
#   api_key = "your_api_key",
#   api_secret = "your_api_secret",
# )
#
# image_file_path = r"D:\Hee\pycharmproject\DrugX\pic\kai.JPG"
#
# response = upload(image_file_path)
#
# image_url = response['url']
#
# print('Image URL:', image_url)










from chemspipy import ChemSpider
import pubchempy as pcp

cs = ChemSpider('GJjrQLtK80AczVd34CTS0GSh4fNAOkVQ')

c = pcp.Compound.from_cid(715)

print(c.isomeric_smiles)



# data = {
#     "drug": [
#         {
#             "cid_": 9892366,
#             "molecular_formula": "C28H28N4O3",
#             "molecular_weight": "468.5",
#             "isomeric_smiles": "CN(C)CC1CCN2C=C(C3=CC=CC=C32)C4=C(C5=CN(CCO1)C6=CC=CC=C65)C(=O)NC4=O",
#             "iupac_name": "18-[(dimethylamino)methyl]-17-oxa-4,14,21-triazahexacyclo[19.6.1.17,14.02,6.08,13.022,27]nonacosa-1(28),2(6),7(29),8,10,12,22,24,26-nonaene-3,5-dione",
#             "xlogp": 2.7,
#             "rotatable_bond_count": 2,
#             "url_": "http://www.chemspider.com/ImagesHandler.ashx?id=9892366&w=500&h=500&bgcolor=white"
#         }
#     ],
#     "protein": [
#         {
#             "pdb_id": "5IMT",
#             "seq": "NSEAAKKALNDYIWGLQYDKLNILTHQGEKLKNHSSREAFHRPGEYVVIEKKKQSISNATSKLSVSSANDDRIFPGALLKADQSLLENLPTLIPVNRGKTTISVNLPGLKNGESNLTVENPSNSTVRTAVNNLVEKWIQNYSKTHAVPARMQYESISAQSMSQLQAKFGADFSKVGAPLNVDFSSVHKGEKQVFIANFRQVYYTASVDSPNSPSALFGSGITPTDLINRGVNSKTPPVYVSNVSYGRAMYVKFETTSKSTKVQAAIDAVVK",
#             "deposit_date": "2016-03-06T00:00:00+0000",
#             "release_date": "2016-08-24T00:00:00+0000",
#             "molecular_weight": 68.89,
#             "nonpolymer_bound_components": [
#                 "CU",
#                 "ZN"
#             ],
#             "pdbx_keywords": "TOXIN",
#             "image_url": "http://res.cloudinary.com/dutuzuhwu/image/upload/v1681291709/iwqkzuxlkarndjcwqxib.png"
#         },
#         {
#             "pdb_id": "2H84",
#             "seq": "NNSFVLGIGISVPGEPISQQSLKDSISNDFSDKAETNEKVKRIFEQSQIKTRHLVRDYTKPENSIKFRHLETITDVNNQFKKVVPDLAQQACLRALKDWGGDKGDITHIVSVTSTGIIIPDVNFKLIDLLGLNKDVERVSLNLMGCLAGLSSLRTAASLAKASPRNRILVVCTEVCSLHFSNTDGGDQMVASSIFADGSAAYIIGCNPRIEETPLYEVMCSINRSFPNTENAMVWDLEKEGWNLGLDASIPIVIGSGIEAFVDTLLDKAKLQTSTAISAKDCEFLIHTGGKSILMNIENSLGIDPKQTKNTWDVYHAYGNMSSASVIFVMDHARKSKSLPTYSISLAFGPGLAFEGCFLKNVV",
#             "deposit_date": "2006-06-06T00:00:00+0000",
#             "release_date": "2006-08-22T00:00:00+0000",
#             "molecular_weight": 82.04,
#             "nonpolymer_bound_components": "NOT FOUND",
#             "pdbx_keywords": "BIOSYNTHETIC PROTEIN, TRANSFERASE",
#             "image_url": "http://res.cloudinary.com/dutuzuhwu/image/upload/v1681301166/rpwf9jeyx54zpv88npod.png"
#         },
#         {
#             "drugx_id": "1CQ4",
#             "seq": "KTEWPELVGKSVEEAKKVILQDKPEAQIIVLPVGTIV",
#             "deposit_date": "1998-11-17T00:00:00+0000",
#             "release_date": "1998-11-25T00:00:00+0000",
#             "molecular_weight": 8.19,
#             "nonpolymer_bound_components": "NOT FOUND",
#             "pdbx_keywords": "HYDROLASE INHIBITOR",
#             "image_url": "http://res.cloudinary.com/dutuzuhwu/image/upload/v1681292458/jhfqsuoiisjf3glkjxxt.png"
#         },
#         {
#             "pdb_id": "1D4X",
#             "seq": "EVAALVVDNGSGMCKAGFAGDDAPRAVFPSIVGRPRHQGV",
#             "deposit_date": "1999-10-06T00:00:00+0000",
#             "release_date": "2001-05-02T00:00:00+0000",
#             "molecular_weight": 56.64,
#             "nonpolymer_bound_components": [
#                 "ATP",
#                 "CA",
#                 "MG"
#             ],
#             "pdbx_keywords": "CONTRACTILE PROTEIN",
#             "image_url": "http://res.cloudinary.com/dutuzuhwu/image/upload/v1681301180/r7kw09efxrrn74sgdzu2.png"
#         }
#     ],
#     "prob": [
#         0.3985659182071686,
#         0.4639686644077301,
#         0.3766278624534607,
#         0.37480732798576355
#     ]
# }
#



