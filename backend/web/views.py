import json
import traceback
import os
import sys
import uuid
import csv
from pathlib import Path
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from chemspipy import ChemSpider
import pubchempy as pcp


from web.ms import User
from web.serializer import UserModelSerializer
from web.drug_services import build_drug_entry_from_cid, build_fallback_drug_entry, get_drug_info, get_drug_info_by_cid
from web.protein_services import (
    ProteinNotFoundError,
    query_complex_info,
    query_protein_info,
    resolve_pdb_protein_info,
    resolve_protein_info,
)
from web.personalization import (
    build_patient_profile,
    enrich_drug_with_metadata_status,
    find_metadata_for_drug,
    get_personalization_options,
    has_personalization_input,
    rerank_drugs,
)
from web.prediction_model_services import TASK_CONFIG, predict_hyperattention_scores, run_prediction_task
from web.demo_cache import (
    get_dti_recommendation_demo_result,
    get_personalized_recommend_demo_result,
    get_prediction_model_demo_result,
    get_structure_query_demo_result,
)
from web.models import DiseaseRecommendation  

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))


cs = ChemSpider('GJjrQLtK80AczVd34CTS0GSh4fNAOkVQ')


def _read_csv_summary(csv_path, description, preview_limit=25):
    csv_path = Path(csv_path)
    source = {
        'file_name': csv_path.name,
        'path': str(csv_path.relative_to(settings.BASE_DIR)).replace('\\', '/') if csv_path.exists() else str(csv_path.name),
        'record_count': 0,
        'fields': [],
        'preview_rows': [],
        'description': description,
        'status': 'missing',
    }
    if not csv_path.exists():
        return source

    try:
        with csv_path.open('r', encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            source['fields'] = list(reader.fieldnames or [])
            rows = []
            total = 0
            for row in reader:
                total += 1
                if len(rows) < preview_limit:
                    rows.append(row)
            source['record_count'] = total
            source['preview_rows'] = rows
            source['status'] = 'ready' if total > 0 else 'empty'
    except Exception:
        source['status'] = 'error'
    return source


def _split_sequence_like_input(raw_text):
    text = str(raw_text or "").replace("\r", "\n").replace("；", ";").strip()
    if not text:
        return []

    if "\n" in text:
        parts = text.split("\n")
    elif ";" in text:
        parts = text.split(";")
    else:
        parts = [text]
    return [part.strip() for part in parts if part.strip()]


def _build_drug_entry_from_smiles(smiles, index):
    smiles_text = str(smiles or "").strip()
    drug_info = {
        "drugx_id": "",
        "drug_name": "",
        "molecular_formula": "",
        "molecular_weight": "",
        "iupac_name": f"Drug_{index}",
        "xlogp": "",
        "rotatable_bond_count": "",
        "url_": "",
        "canonical_smiles": smiles_text,
        "isomeric_smiles": smiles_text,
        "smiles": smiles_text,
    }
    metadata, _ = find_metadata_for_drug(drug_info)
    if metadata:
        drug_info["drugx_id"] = str(metadata.get("pubchem_cid", "")).strip()
        display_name = str(metadata.get("drug_name", "")).strip()
        if display_name:
            drug_info["drug_name"] = display_name
            drug_info["iupac_name"] = display_name
    return drug_info



class RegisterView(APIView):
    """User registration view."""

    def post(self, request):
        print("=" * 60)

        try:
            username = request.data.get('userName') or request.data.get('username')
            password = request.data.get('password')
            phone = request.data.get('phoneNumber') or request.data.get('phone')

            if not username or not password:
                return Response("false_0", status=status.HTTP_400_BAD_REQUEST)

            if User.objects.filter(username=username).exists():
                return Response("false_1", status=status.HTTP_409_CONFLICT)

            user_data = {'username': username, 'password': password}
            if phone:
                user_data['phone'] = phone

            serializer = UserModelSerializer(data=user_data)
            if serializer.is_valid():
                serializer.save()
                return Response("true", status=status.HTTP_201_CREATED)
            return Response("false_2", status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "error": "Registration failed",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





class LoginView(APIView):
    """User login view."""

    def post(self, request):
        print("=" * 60)

        try:
            username = request.data.get('userName') or request.data.get('username')
            password = request.data.get('password')

            if not username or not password:
                return Response("false_0", status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.filter(username=username).first()
            if not user:
                return Response("false_1", status=status.HTTP_404_NOT_FOUND)

            if password == user.password:
                request.session['username'] = username
                return Response("true", status=status.HTTP_200_OK)
            return Response("false_2", status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            return Response({
                "error": "Login failed",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only POST is allowed'
        }, status=405)

    request.session.flush()
    return JsonResponse({
        'status': 'success'
    }, status=200)


def current_user_view(request):
    if request.method != 'GET':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only GET is allowed'
        }, status=405)

    username = request.session.get('username')
    if not username:
        return JsonResponse({
            'status': 'error',
            'code': 'UNAUTHORIZED',
            'message': 'Please login first'
        }, status=401)

    user = User.objects.filter(username=username).first()
    if not user:
        request.session.flush()
        return JsonResponse({
            'status': 'error',
            'code': 'USER_NOT_FOUND',
            'message': 'Current user does not exist'
        }, status=404)

    return JsonResponse({
        'status': 'success',
        'logged_in': True,
        'user': {
            'username': user.username
        }
    }, status=200)



class DrugView(APIView):
   

    def post(self, request):
        try:
            data = request.data
            print(f"Drug query payload: {data}")

     
            if not data or 'selectOp' not in data or 'inputText' not in data:
                return Response({
                    "error": "Missing required parameters: selectOp or inputText"
                }, status=status.HTTP_400_BAD_REQUEST)

            op = data['selectOp']
            input_text = data['inputText'].strip()

            if not input_text:
                return Response({
                    "error": "Input text is required"
                }, status=status.HTTP_400_BAD_REQUEST)

            demo_result = get_structure_query_demo_result("drug", op, input_text)
            if demo_result is not None:
                return Response(demo_result, status=status.HTTP_200_OK)

            compound = None
            c = None

           
            if op == '1':
                compounds = pcp.get_compounds(input_text, 'smiles')
                if not compounds:
                    return Response({
                        "error": "No compound was found for the provided SMILES input"
                    }, status=status.HTTP_404_NOT_FOUND)
                c = compounds[0]
                try:
                    compound = cs.get_compound(c.cid)
                except:
                    compound = None  
            
            else:
                if not input_text.isdigit():
                    return Response({
                        "error": "CID must be numeric"
                    }, status=status.HTTP_400_BAD_REQUEST)

                cid = int(input_text)
                try:
                    drug_info = get_drug_info_by_cid(cid)
                except Exception as pubchem_e:
                    print(f"PubChem query failed: {pubchem_e}")
                    return Response({
                        "error": "Failed to access PubChem API",
                        "detail": "Please check whether the CID is valid, for example: 2244."
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                return Response(drug_info, status=status.HTTP_200_OK)

           
            drug_info = get_drug_info(compound, c)
            return Response(drug_info, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Drug query failed: {traceback.format_exc()}")
            return Response({
                "error": "Drug query failed",
                "detail": str(e),
                "suggestion": "Please verify the query input or upstream API availability."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProteinView(APIView):
    """Legacy local protein query view."""

    def post(self, request):
        try:
          
            data = request.data
            print(f"Legacy protein query payload: {data}")

            info = {}
            if isinstance(data, dict):
                if len(data) == 1 and list(data.keys())[0].startswith('{'):
                    info = json.loads(list(data.keys())[0])
                else:
                    info = data
            elif isinstance(data, str):
                info = json.loads(data)
            else:
                return Response({
                    "error": "Invalid request payload format"
                }, status=400)

            
            op = info.get('selectOp')
            input_text = info.get('inputText', '').strip().upper()

            if not input_text:
                return Response({
                    "error": "Input text is required"
                }, status=400)

            
            PDB_FILES_DIR = os.path.join(settings.BASE_DIR, 'pic')

            
            pdb_id = ""
            if op == '2':  # PDB ID query
                pdb_id = input_text
            else:  
                pdb_id = "5IMT"

            
            png_file = os.path.join(PDB_FILES_DIR, f"{pdb_id}.png")
            if not os.path.exists(png_file):
                
                for filename in os.listdir(PDB_FILES_DIR):
                    if filename.lower() == f"{pdb_id.lower()}.png":
                        pdb_id = filename.split('.')[0].upper()
                        png_file = os.path.join(PDB_FILES_DIR, filename)
                        break
                else:
                    return Response({
                        "error": f"Local image not found for PDB ID: {input_text}"
                    }, status=404)

            
            pdb_mock_data = {
                "5IMT": {
                    "pdb_id": "5IMT",
                    "seq": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN",
                    "deposit_date": "2015-06-25",
                    "release_date": "2015-09-23",
                    "molecular_weight": "5808.0",
                    "nonpolymer_bound_components": "ZINC ION, WATER",
                    "pdbx_keywords": "INSULIN, HORMONE, STRUCTURE",
                    "image_url": f"/pic/{pdb_id}.png"
                },
                "1CQ4": {
                    "pdb_id": "1CQ4",
                    "seq": "YOUR_SEQUENCE_HERE",
                    "deposit_date": "2000-01-01",
                    "release_date": "2000-04-01",
                    "molecular_weight": "12345.0",
                    "nonpolymer_bound_components": "Water",
                    "pdbx_keywords": "PROTEIN",
                    "image_url": f"/pic/{pdb_id}.png"
                }
            }

            
            pdb_info = pdb_mock_data.get(pdb_id, pdb_mock_data["5IMT"])
            if op != '2':
                pdb_info["seq"] = input_text
            pdb_info["image_url"] = f"/pic/{pdb_id}.png"

            return Response(pdb_info, status=200)

        except Exception as e:
            print(f"Legacy protein query failed: {str(e)}")
            traceback.print_exc()
            return Response({
                "error": "Protein query failed",
                "details": str(e)
            }, status=500)



class ProteinView(APIView):
    """Protein query view supporting PDB and UniProt lookup."""

    def post(self, request):
        try:
            data = request.data
            print(f"Protein query payload: {data}")

            info = {}
            if isinstance(data, dict):
                if len(data) == 1 and list(data.keys())[0].startswith('{'):
                    info = json.loads(list(data.keys())[0])
                else:
                    info = data
            elif isinstance(data, str):
                info = json.loads(data)
            else:
                return Response({
                    "error": "Invalid request payload format"
                }, status=400)

            op = info.get('selectOp')
            input_text = info.get('inputText', '').strip()

            if not input_text:
                return Response({
                    "error": "Input text is required"
                }, status=400)

            demo_result = get_structure_query_demo_result("protein", op, input_text)
            if demo_result is not None:
                return Response(demo_result, status=200)

            protein_info = query_protein_info(op, input_text, settings.BASE_DIR)
            return Response(protein_info, status=200)

        except ProteinNotFoundError as e:
            return Response({
                "error": str(e)
            }, status=404)
        except Exception as e:
            print(f"Protein query failed: {str(e)}")
            traceback.print_exc()
            return Response({
                "error": "Protein query failed",
                "details": str(e)
            }, status=500)


class ComplexView(APIView):
    """Protein-ligand complex query view with local-first cache lookup."""

    def post(self, request):
        try:
            data = request.data
            print(f"Complex query payload: {data}")

            info = {}
            if isinstance(data, dict):
                if len(data) == 1 and list(data.keys())[0].startswith('{'):
                    info = json.loads(list(data.keys())[0])
                else:
                    info = data
            elif isinstance(data, str):
                info = json.loads(data)
            else:
                return Response({"error": "Invalid request payload"}, status=400)

            pdb_id = str(info.get('inputText', '')).strip()
            if not pdb_id:
                return Response({"error": "PDB ID is required"}, status=400)

            demo_result = get_structure_query_demo_result("complex", "", pdb_id)
            if demo_result is not None:
                return Response(demo_result, status=200)

            complex_info = query_complex_info(pdb_id, settings.BASE_DIR)
            return Response(complex_info, status=200)
        except ProteinNotFoundError as exc:
            return Response({"error": str(exc)}, status=404)
        except Exception as exc:
            print(f"Complex query failed: {str(exc)}")
            traceback.print_exc()
            return Response({
                "error": "Complex query failed",
                "details": str(exc)
            }, status=500)


class PredictionModelsRunView(APIView):
    """Task-based prediction entry with explicit task routing."""

    def post(self, request):
        try:
            data = request.data or {}
            task_type = str(data.get("task_type", "")).strip()
            drug_input = str(data.get("drug_input", "")).strip()
            protein_input = str(data.get("protein_input", "")).strip()

            if task_type not in TASK_CONFIG:
                return Response({"error": "Unsupported task type"}, status=400)
            if not drug_input:
                return Response({"error": "Drug input is required"}, status=400)
            if not protein_input:
                return Response({"error": "Protein input is required"}, status=400)

            demo_result = get_prediction_model_demo_result(task_type, drug_input, protein_input)
            if demo_result is not None:
                return Response(demo_result, status=200)

            result = run_prediction_task(task_type, drug_input, protein_input)
            return Response(result, status=200)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except Exception as exc:
            traceback.print_exc()
            return Response({
                "error": "Prediction workflow failed",
                "detail": str(exc)
            }, status=500)



class DTI(APIView):
    """Legacy DTI prediction view."""

    def post(self, request):
        try:
            
            data = request.data
            print(f"Legacy DTI request payload: {data}")

            info = {}
            if isinstance(data, dict):
                if len(data) == 1 and list(data.keys())[0].startswith('{'):
                    json_str = list(data.keys())[0]
                    json_str = json_str.replace("；", ";")
                    info = json.loads(json_str)
                else:
                    info = data
            elif isinstance(data, str):
                data = data.replace("；", ";")
                info = json.loads(data)
            else:
                return Response({
                    "error": "Invalid request payload format"
                }, status=400)

            
            input_pdb_ids = info.get('input1', '').strip().replace("；", ";")
            input_cids = info.get('input2', '').strip().replace("；", ";")
            patient_profile = build_patient_profile(
                age=info.get('age'),
                sex=info.get('sex'),
                disease_history=info.get('disease_history'),
                allergy_history=info.get('allergy_history'),
                insurance_preference=info.get('insurance_preference'),
            )

            if not input_pdb_ids or not input_cids:
                return Response({
                    "error": "PDB IDs and CIDs are required"
                }, status=400)

            
            pdb_list = [pdb.strip() for pdb in input_pdb_ids.split(',') if pdb.strip()]
            cid_list = [cid.strip() for cid in input_cids.split(',') if cid.strip()]

            if not cid_list or not pdb_list:
                return Response({
                    "error": "PDB IDs and CIDs are required"
                }, status=400)

            
            drug_info_list = []
            smi_list = []
            for cid in cid_list:
                try:
                    drug_info, smiles = build_drug_entry_from_cid(cid)
                    drug_info_list.append(drug_info)
                    smi_list.append(smiles)
                except Exception as e:
                    print(f"CID {cid} lookup failed: {str(e)}")
                    drug_info, smiles = build_fallback_drug_entry(cid)
                    drug_info_list.append(drug_info)
                    smi_list.append(smiles)

            
            pdb_info_list = []
            seq_list = []
            for pdb_id in pdb_list:
                try:
                    pdb_info = resolve_pdb_protein_info(pdb_id, settings.BASE_DIR)
                    pdb_seq = str(pdb_info.get("seq", "")).strip() or "MOCK_SEQUENCE"
                    pdb_info["seq"] = pdb_seq
                    pdb_info_list.append(pdb_info)
                    seq_list.append(pdb_seq)
                except Exception as e:
                    print(f"PDB {pdb_id} ????: {str(e)}")
                    pdb_info_list.append({
                        "pdb_id": pdb_id,
                        "uniprot_id": "",
                        "source": "mock",
                        "seq": "MOCK_SEQUENCE",
                        "deposit_date": "NOT FOUND",
                        "release_date": "NOT FOUND",
                        "molecular_weight": "NOT FOUND",
                        "nonpolymer_bound_components": "NOT FOUND",
                        "pdbx_keywords": "MOCK PROTEIN",
                        "image_url": "/pic/5IMT.png"
                    })
                    seq_list.append("MOCK_SEQUENCE")

            
            try:
                prob_list = predict_hyperattention_scores(
                    "`n".join(smi_list),
                    "`n".join(seq_list),
                )
            except Exception as e:
                print(f"DTI prediction failed: {str(e)}")
                prob_list = [0.0] * max(1, len(smi_list) * len(seq_list))


            
            personalization_applied = False
            ranked_results = []
            if has_personalization_input(patient_profile):
                try:
                    ranked_results = rerank_drugs(drug_info_list, prob_list, patient_profile)
                    personalization_applied = True
                except Exception as rerank_error:
                    print(f"Personalized reranking failed: {str(rerank_error)}")
                    traceback.print_exc()

            drug_info_with_status = [enrich_drug_with_metadata_status(drug) for drug in drug_info_list]

            response_data = {
                "drug": drug_info_with_status,
                "protein": pdb_info_list,
                "prob": prob_list,
                "personalization_applied": personalization_applied,
                "patient_profile": patient_profile,
                "ranked_results": ranked_results
            }

            return Response(response_data, status=200)

        except Exception as e:
            print(f"DTI prediction failed: {str(e)}")
            traceback.print_exc()
            return Response({
                "error": "DTI prediction failed",
                "details": str(e)
            }, status=500)



# Override the legacy DTI view with the personalized recommendation flow.
class DTI(APIView):
    """DTI prediction endpoint for personalized recommendation."""

    def post(self, request):
        try:
            data = request.data
            print(f"DTI request payload: {data}")

            if isinstance(data, dict):
                info = json.loads(list(data.keys())[0]) if len(data) == 1 and list(data.keys())[0].startswith('{') else data
            elif isinstance(data, str):
                info = json.loads(data)
            else:
                return Response({"error": "Invalid request payload."}, status=400)

            input_protein_sequences = str(info.get("input1", "")).strip()
            input_drug_smiles = str(info.get("input2", "")).strip()
            if not input_protein_sequences or not input_drug_smiles:
                return Response({"error": "Drug SMILES and protein sequence are required."}, status=400)

            required_fields = {
                "age": info.get("age"),
                "sex": info.get("sex"),
                "disease_history": info.get("disease_history"),
                "allergy_history": info.get("allergy_history"),
                "insurance_preference": info.get("insurance_preference"),
            }
            if any(
                value in (None, "") or (isinstance(value, list) and not value)
                for value in required_fields.values()
            ):
                return Response(
                    {"error": "Age, sex, disease history, allergy history, and insurance preference are all required."},
                    status=400,
                )

            demo_result = get_dti_recommendation_demo_result(info)
            if demo_result is not None:
                return Response(demo_result, status=200)

            patient_profile = build_patient_profile(
                age=info.get("age"),
                sex=info.get("sex"),
                disease_history=info.get("disease_history"),
                allergy_history=info.get("allergy_history"),
                insurance_preference=info.get("insurance_preference"),
            )

            protein_sequence_list = _split_sequence_like_input(input_protein_sequences)
            drug_smiles_list = _split_sequence_like_input(input_drug_smiles)
            if not protein_sequence_list or not drug_smiles_list:
                return Response({"error": "Drug SMILES and protein sequence are required."}, status=400)

            drug_info_list = []
            smi_list = []
            for index, smiles in enumerate(drug_smiles_list, start=1):
                drug_info = _build_drug_entry_from_smiles(smiles, index)
                drug_info_list.append(drug_info)
                smi_list.append(smiles)

            protein_info_list = []
            seq_list = []
            for index, sequence in enumerate(protein_sequence_list, start=1):
                normalized_sequence = str(sequence).strip().upper()
                if not normalized_sequence:
                    continue
                protein_id = f"SEQ_{index}"
                protein_info_list.append(
                    {
                        "pdb_id": protein_id,
                        "protein_id": protein_id,
                        "uniprot_id": "",
                        "source": "sequence",
                        "seq": normalized_sequence,
                        "deposit_date": "NOT APPLICABLE",
                        "release_date": "NOT APPLICABLE",
                        "molecular_weight": "NOT APPLICABLE",
                        "nonpolymer_bound_components": "NOT APPLICABLE",
                        "pdbx_keywords": "PROTEIN SEQUENCE INPUT",
                        "image_url": "/pic/5IMT.png",
                    }
                )
                seq_list.append(normalized_sequence)

            try:
                prob_list = predict_hyperattention_scores(
                    "\n".join(smi_list),
                    "\n".join(seq_list),
                )
                for smi in smi_list:
                    for seq in seq_list:
                        score_index = (smi_list.index(smi) * len(seq_list)) + seq_list.index(seq)
                        if score_index < len(prob_list):
                            print(f"DTI prediction: SMILES={smi[:20]}..., SEQ={seq[:20]}..., prob={prob_list[score_index]}")
            except Exception as error:
                print(f"DTI prediction failed: {str(error)}")
                prob_list = [0.0 for _ in range(len(smi_list) * len(seq_list))]

            ranked_results = []
            personalization_applied = False
            if has_personalization_input(patient_profile):
                try:
                    ranked_results = rerank_drugs(drug_info_list, prob_list, patient_profile)
                    personalization_applied = True
                except Exception as rerank_error:
                    print(f"Personalized reranking failed: {str(rerank_error)}")
                    traceback.print_exc()

            response_data = {
                "drug": [enrich_drug_with_metadata_status(drug) for drug in drug_info_list],
                "protein": protein_info_list,
                "prob": prob_list,
                "personalization_applied": personalization_applied,
                "patient_profile": patient_profile,
                "ranked_results": ranked_results,
            }
            return Response(response_data, status=200)

        except Exception as e:
            print(f"DTI prediction failed: {str(e)}")
            traceback.print_exc()
            return Response({"error": "DTI prediction failed", "details": str(e)}, status=500)


@csrf_exempt
def personalized_recommend(request):
    """Personalized recommendation endpoint based on DiseaseRecommendation."""
    if request.method == 'POST':
        
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
        except Exception as e:
            print(f"Failed to parse request payload: {e}")
            data = request.data or request.POST

       
        disease = data.get('disease_type') or data.get('disease') or data.get('illness')
        age = data.get('age', 0)
        gender = data.get('gender', 'Any') or 'Any'

        
        try:
            age = int(age) if age and str(age).isdigit() else 0
        except:
            age = 0

        
        if not disease:
            return JsonResponse({
                'status': 'error',
                'code': 'MISSING_PARAM',
                'message': 'Missing disease type parameter: disease_type/disease/illness'
            }, status=400)

        demo_result = get_personalized_recommend_demo_result(disease, age, gender)
        if demo_result is not None:
            return JsonResponse(demo_result, status=200)

        try:
            
            query = Q()
            
            query &= Q(disease_type__icontains=disease)
            
            if age > 0:
                query &= (
                        Q(age_min__lte=age, age_max__gte=age) |
                        Q(age_min__isnull=True) |
                        Q(age_max__isnull=True)
                )
            
            query &= Q(gender__in=[gender, 'Any'])

            
            recommendations = DiseaseRecommendation.objects.filter(query).order_by(
                'priority',  
                'price_ref'  
            )[:10]

            
            results = []
            for idx, rec in enumerate(recommendations, 1):
                
                age_range = "Unlimited"
                if rec.age_min is not None and rec.age_max is not None:
                    age_range = f"{rec.age_min}-{rec.age_max}"
                elif rec.age_min is not None:
                    age_range = f"{rec.age_min} and above"
                elif rec.age_max is not None:
                    age_range = f"{rec.age_max} and below"

                results.append({
                    'rank': idx,
                    'drug': rec.drug_name,
                    'reason': rec.reason,
                    'price': rec.price_ref,
                    'medicare': rec.medicare_cn,
                    'usage': rec.usage_summary,
                    'priority': rec.priority,
                    'match_age_range': age_range,
                    'match_gender': rec.gender
                })

            
            return JsonResponse({
                'status': 'success',
                'code': 'SUCCESS',
                'request_params': {
                    'disease': disease,
                    'age': age,
                    'gender': gender
                },
                'count': len(results),
                'recommendations': results
            }, status=200)

        except Exception as e:
            error_msg = f"Personalized recommendation query failed: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return JsonResponse({
                'status': 'error',
                'code': 'DB_ERROR',
                'message': 'Database query failed. Please contact the administrator.',
                'detail': str(e)
            }, status=500)

    # Reject unsupported HTTP methods.
    return JsonResponse({
        'status': 'error',
        'code': 'METHOD_NOT_ALLOWED',
        'message': 'Only POST requests are supported'
    }, status=405)


@csrf_exempt
def personalization_options(request):
    if request.method != 'GET':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only GET is allowed'
        }, status=405)

    return JsonResponse({
        'status': 'success',
        'options': get_personalization_options()
    }, status=200)


@csrf_exempt
def save_recommendation_result(request):
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only POST is allowed'
        }, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body or '{}')
        else:
            data = request.POST
    except Exception as exc:
        return JsonResponse({
            'status': 'error',
            'code': 'BAD_REQUEST',
            'message': 'Invalid request payload',
            'detail': str(exc)
        }, status=400)

    result_payload = data.get('result_payload')
    if isinstance(result_payload, str):
        try:
            result_payload = json.loads(result_payload)
        except json.JSONDecodeError:
            result_payload = None

    if not isinstance(result_payload, dict):
        return JsonResponse({
            'status': 'error',
            'code': 'MISSING_RESULT',
            'message': 'result_payload is required'
        }, status=400)

    user_name = _current_session_username(request)
    if not user_name:
        return JsonResponse({
            'status': 'error',
            'code': 'UNAUTHORIZED',
            'message': 'Please login first'
        }, status=401)

    save_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
    save_dir = _user_saved_recommendations_dir(user_name)
    save_path = save_dir / f'{save_id}.json'

    save_payload = {
        'save_id': save_id,
        'saved_at': datetime.now().isoformat(),
        'user_name': user_name,
        'result_payload': result_payload,
    }

    try:
        with save_path.open('w', encoding='utf-8') as file:
            json.dump(save_payload, file, ensure_ascii=False, indent=2)
    except OSError as exc:
        return JsonResponse({
            'status': 'error',
            'code': 'SAVE_FAILED',
            'message': 'Failed to save recommendation result',
            'detail': str(exc)
        }, status=500)

    return JsonResponse({
        'status': 'success',
        'save_id': save_id,
        'saved_at': save_payload['saved_at'],
        'file_name': save_path.name,
    }, status=200)


def _saved_recommendations_dir():
    save_dir = settings.BASE_DIR / 'saved_recommendations'
    save_dir.mkdir(parents=True, exist_ok=True)
    return save_dir


def _current_session_username(request):
    username = request.session.get('username')
    if not username:
        return None
    return str(username).strip() or None


def _user_saved_recommendations_dir(username):
    user_dir = _saved_recommendations_dir() / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _legacy_saved_recommendation_paths():
    root_dir = _saved_recommendations_dir()
    return [path for path in root_dir.glob('*.json') if path.is_file()]


def _demo_saved_recommendation_paths():
    demo_dir = _saved_recommendations_dir() / 'demo'
    if not demo_dir.exists():
        return []
    return [path for path in demo_dir.glob('*.json') if path.is_file()]


def _is_demo_saved_recommendation(payload):
    result_payload = payload.get('result_payload') or {}
    return bool(
        payload.get('demo_record')
        or result_payload.get('demo_record')
        or str(payload.get('user_name', '')).strip() == 'demo'
    )


def _read_saved_recommendation(path):
    with path.open('r', encoding='utf-8') as file:
        return json.load(file)


def _saved_result_status_summary(result_payload):
    ranked_results = result_payload.get('ranked_results') or []
    drug_results = result_payload.get('drug') or []
    source_items = ranked_results or drug_results

    levels = []
    for item in source_items:
        status_info = item.get('metadata_status') or {}
        level = str(status_info.get('level', '')).strip().lower()
        if level:
            levels.append(level)

    if not levels:
        return {
            'level': 'unknown',
            'label': 'Information incomplete',
        }
    if 'unknown' in levels:
        return {
            'level': 'unknown',
            'label': 'Contains incomplete information results',
        }
    if 'compound_only' in levels:
        return {
            'level': 'compound_only',
            'label': 'Structure-only results',
        }
    return {
        'level': 'full',
        'label': 'Complete information',
    }


@csrf_exempt
def saved_recommendation_list(request):
    if request.method != 'GET':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only GET is allowed'
        }, status=405)

    user_name = _current_session_username(request)
    if not user_name:
        return JsonResponse({
            'status': 'error',
            'code': 'UNAUTHORIZED',
            'message': 'Please login first'
        }, status=401)

    items = []

    candidate_paths = list(_user_saved_recommendations_dir(user_name).glob('*.json'))
    candidate_paths.extend(_legacy_saved_recommendation_paths())
    candidate_paths.extend(_demo_saved_recommendation_paths())

    seen_ids = set()
    for path in sorted(candidate_paths, reverse=True):
        try:
            payload = _read_saved_recommendation(path)
        except (OSError, json.JSONDecodeError):
            continue

        payload_user = str(payload.get('user_name', '')).strip()
        is_demo = _is_demo_saved_recommendation(payload)
        if payload_user != user_name and not is_demo:
            continue
        save_id = payload.get('save_id')
        if not save_id or save_id in seen_ids:
            continue
        seen_ids.add(save_id)
        result_payload = payload.get('result_payload') or {}
        status_summary = _saved_result_status_summary(result_payload)
        items.append({
            'save_id': save_id,
            'saved_at': payload.get('saved_at'),
            'user_name': payload_user,
            'is_demo': is_demo,
            'file_name': path.name,
            'personalization_applied': bool(result_payload.get('personalization_applied')),
            'drug_count': len(result_payload.get('drug') or []),
            'protein_count': len(result_payload.get('protein') or []),
            'ranked_count': len(result_payload.get('ranked_results') or []),
            'status_summary': status_summary,
        })

    return JsonResponse({
        'status': 'success',
        'count': len(items),
        'results': items,
    }, status=200)


@csrf_exempt
def saved_recommendation_detail(request, save_id):
    if request.method != 'GET':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only GET is allowed'
        }, status=405)

    user_name = _current_session_username(request)
    if not user_name:
        return JsonResponse({
            'status': 'error',
            'code': 'UNAUTHORIZED',
            'message': 'Please login first'
        }, status=401)

    target_path = _user_saved_recommendations_dir(user_name) / f'{save_id}.json'
    fallback_path = _saved_recommendations_dir() / f'{save_id}.json'
    demo_path = _saved_recommendations_dir() / 'demo' / f'{save_id}.json'

    if not target_path.exists() and fallback_path.exists():
        target_path = fallback_path
    if not target_path.exists() and demo_path.exists():
        target_path = demo_path

    if not target_path.exists():
        return JsonResponse({
            'status': 'error',
            'code': 'NOT_FOUND',
            'message': 'Saved recommendation not found'
        }, status=404)

    try:
        payload = _read_saved_recommendation(target_path)
    except (OSError, json.JSONDecodeError) as exc:
        return JsonResponse({
            'status': 'error',
            'code': 'READ_FAILED',
            'message': 'Failed to read saved recommendation',
            'detail': str(exc)
        }, status=500)

    if str(payload.get('user_name', '')).strip() != user_name and not _is_demo_saved_recommendation(payload):
        return JsonResponse({
            'status': 'error',
            'code': 'FORBIDDEN',
            'message': 'You do not have access to this saved recommendation'
        }, status=403)

    return JsonResponse({
        'status': 'success',
        'data': payload,
    }, status=200)


@csrf_exempt
def saved_recommendation_delete(request, save_id):
    if request.method not in ('POST', 'DELETE'):
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only POST or DELETE is allowed'
        }, status=405)

    user_name = _current_session_username(request)
    if not user_name:
        return JsonResponse({
            'status': 'error',
            'code': 'UNAUTHORIZED',
            'message': 'Please login first'
        }, status=401)

    target_path = _user_saved_recommendations_dir(user_name) / f'{save_id}.json'
    fallback_path = _saved_recommendations_dir() / f'{save_id}.json'
    demo_path = _saved_recommendations_dir() / 'demo' / f'{save_id}.json'

    if not target_path.exists() and fallback_path.exists():
        target_path = fallback_path
    if not target_path.exists() and demo_path.exists():
        target_path = demo_path

    if not target_path.exists():
        return JsonResponse({
            'status': 'error',
            'code': 'NOT_FOUND',
            'message': 'Saved recommendation not found'
        }, status=404)

    try:
        payload = _read_saved_recommendation(target_path)
    except (OSError, json.JSONDecodeError) as exc:
        return JsonResponse({
            'status': 'error',
            'code': 'READ_FAILED',
            'message': 'Failed to read saved recommendation',
            'detail': str(exc)
        }, status=500)

    if _is_demo_saved_recommendation(payload):
        return JsonResponse({
            'status': 'error',
            'code': 'DEMO_RECORD',
            'message': 'Demo records cannot be deleted'
        }, status=403)

    if str(payload.get('user_name', '')).strip() != user_name:
        return JsonResponse({
            'status': 'error',
            'code': 'FORBIDDEN',
            'message': 'You do not have access to delete this saved recommendation'
        }, status=403)

    try:
        target_path.unlink()
    except OSError as exc:
        return JsonResponse({
            'status': 'error',
            'code': 'DELETE_FAILED',
            'message': 'Failed to delete saved recommendation',
            'detail': str(exc)
        }, status=500)

    return JsonResponse({
        'status': 'success',
        'save_id': save_id,
        'message': 'Saved recommendation deleted successfully'
    }, status=200)


def data_sources_summary(request):
    if request.method != 'GET':
        return JsonResponse({
            'status': 'error',
            'code': 'METHOD_NOT_ALLOWED',
            'message': 'Only GET is allowed'
        }, status=405)

    data_root = Path(settings.BASE_DIR)
    local_sources = [
        {
            'key': 'drug_structure_data',
            'title': 'Drug Structure Data',
            **_read_csv_summary(
                data_root / 'cid_smiles_map.csv',
                'Used for drug lookup, structure caching, and prediction input.',
            ),
        },
        {
            'key': 'protein_structure_data',
            'title': 'Protein Structure Data',
            **_read_csv_summary(
                data_root / 'pdb_protein_map.csv',
                'Used for protein lookup, local sequence caching, and model input support.',
            ),
        },
        {
            'key': 'personalized_metadata',
            'title': 'Personalized Metadata',
            **_read_csv_summary(
                data_root / 'drug_personalization_metadata.csv',
                'Used for personalized reranking, contraindication checks, and explanation generation.',
            ),
        },
        {
            'key': 'disease_tags',
            'title': 'Disease Tags',
            **_read_csv_summary(
                data_root / 'disease_tag_dict.csv',
                'Used to normalize disease history and match disease-related personalization rules.',
            ),
        },
        {
            'key': 'allergy_tags',
            'title': 'Allergy Tags',
            **_read_csv_summary(
                data_root / 'allergy_tag_dict.csv',
                'Used to normalize allergy history and trigger allergy-aware ranking penalties.',
            ),
        },
    ]

    external_sources = [
        {
            'key': 'pubchem',
            'title': 'PubChem',
            'description': 'Reference source for CID, SMILES, molecular formula, and molecular weight.',
            'type': 'external_reference',
            'status': 'available',
        },
        {
            'key': 'rcsb_pdb',
            'title': 'RCSB PDB',
            'description': 'Reference source for protein structures, sequences, metadata, and structure images.',
            'type': 'external_reference',
            'status': 'available',
        },
        {
            'key': 'uniprot',
            'title': 'UniProt',
            'description': 'Reference source for protein accession mapping and protein annotation support.',
            'type': 'external_reference',
            'status': 'available',
        },
        {
            'key': 'dailymed',
            'title': 'DailyMed',
            'description': 'Reference source for marketed drug labeling, contraindications, and caution notes.',
            'type': 'external_reference',
            'status': 'reference_only',
        },
        {
            'key': 'drugbank',
            'title': 'DrugBank',
            'description': 'Reference source for curated drug metadata and drug-target related annotations.',
            'type': 'external_reference',
            'status': 'reference_only',
        },
    ]

    overview = [
        {
            'key': 'drug_structure_data',
            'title': 'Drug Structure Data',
            'count': next((item['record_count'] for item in local_sources if item['key'] == 'drug_structure_data'), 0),
            'description': 'Drug structure and CID cache for lookup and prediction.',
        },
        {
            'key': 'protein_structure_data',
            'title': 'Protein Structure Data',
            'count': next((item['record_count'] for item in local_sources if item['key'] == 'protein_structure_data'), 0),
            'description': 'Protein sequence and metadata cache for query and prediction.',
        },
        {
            'key': 'personalized_metadata',
            'title': 'Personalized Metadata',
            'count': next((item['record_count'] for item in local_sources if item['key'] == 'personalized_metadata'), 0),
            'description': 'Drug-level metadata used for personalized reranking.',
        },
        {
            'key': 'disease_tags',
            'title': 'Disease Tags',
            'count': next((item['record_count'] for item in local_sources if item['key'] == 'disease_tags'), 0),
            'description': 'Controlled vocabulary for disease history matching.',
        },
        {
            'key': 'allergy_tags',
            'title': 'Allergy Tags',
            'count': next((item['record_count'] for item in local_sources if item['key'] == 'allergy_tags'), 0),
            'description': 'Controlled vocabulary for allergy-aware recommendation rules.',
        },
    ]

    return JsonResponse({
        'status': 'success',
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'overview': overview,
        'local_sources': local_sources,
        'external_sources': external_sources,
    }, status=200)








