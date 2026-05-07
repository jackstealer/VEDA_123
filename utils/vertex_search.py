"""
VEDA — Vertex AI Search (RAG)
Indexes Indian regulatory documents as structured data (NO_CONTENT mode).
"""
import logging
import os
import glob
from utils.config import PROJECT_ID

logger = logging.getLogger(__name__)

DATASTORE_ID = "veda-regulatory-v2"
LOCATION     = "global"
_PARENT      = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection"
_DS_PARENT   = f"{_PARENT}/dataStores/{DATASTORE_ID}/branches/default_branch"


def search_regulatory_context(query: str, industry: str) -> str:
    try:
        from google.cloud import discoveryengine_v1 as discoveryengine
        client         = discoveryengine.SearchServiceClient()
        serving_config = f"{_PARENT}/dataStores/{DATASTORE_ID}/servingConfigs/default_config"
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=f"{industry} {query} India compliance",
            page_size=5,
        )
        response      = client.search(request)
        context_parts = []
        for result in response.results[:5]:
            doc = result.document
            try:
                # struct_data is a protobuf Struct — access via fields
                fields = dict(doc.struct_data.fields)
                content_val = fields.get("content")
                if content_val:
                    text = content_val.string_value[:800]
                    if text:
                        context_parts.append(text)
            except Exception as e:
                pass
        context = "\n\n".join(context_parts)
        logger.info("[VertexSearch] Retrieved %d chars of regulatory context", len(context))
        return context
    except Exception as exc:
        logger.warning("[VertexSearch] Search failed (non-fatal): %s", exc)
        return ""


def setup_datastore() -> bool:
    try:
        from google.cloud import discoveryengine_v1 as discoveryengine

        ds_client = discoveryengine.DataStoreServiceClient()

        # NO_CONTENT mode — data lives in struct_data fields
        datastore = discoveryengine.DataStore(
            display_name="VEDA Regulatory Documents v2",
            industry_vertical=discoveryengine.IndustryVertical.GENERIC,
            solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
            content_config=discoveryengine.DataStore.ContentConfig.NO_CONTENT,
        )
        try:
            op = ds_client.create_data_store(
                parent=_PARENT,
                data_store=datastore,
                data_store_id=DATASTORE_ID,
            )
            op.result(timeout=120)
            logger.info("[VertexSearch] Datastore created: %s", DATASTORE_ID)
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("[VertexSearch] Datastore already exists")
            else:
                raise

        doc_client = discoveryengine.DocumentServiceClient()
        docs_dir   = os.path.join(os.path.dirname(__file__), "..", "regulatory_docs")
        txt_files  = glob.glob(os.path.join(docs_dir, "*.txt"))

        from google.protobuf import struct_pb2

        indexed = 0
        for filepath in txt_files:
            doc_id  = os.path.basename(filepath).replace(".txt", "").replace("_", "-")
            with open(filepath, "r") as f:
                content = f.read()

            struct_data = struct_pb2.Struct()
            struct_data.update({
                "title":    doc_id.replace("-", " ").upper(),
                "content":  content,
                "industry": _detect_industry(doc_id),
                "source":   "Indian Regulatory Framework",
            })

            document = discoveryengine.Document(
                id=doc_id,
                struct_data=struct_data,
            )
            try:
                doc_client.create_document(
                    parent=_DS_PARENT,
                    document=document,
                    document_id=doc_id,
                )
                logger.info("[VertexSearch] Indexed: %s", doc_id)
                indexed += 1
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info("[VertexSearch] Already indexed: %s", doc_id)
                    indexed += 1
                else:
                    logger.warning("[VertexSearch] Failed %s: %s", doc_id, e)

        logger.info("[VertexSearch] Done — %d/%d docs indexed", indexed, len(txt_files))
        return indexed > 0

    except Exception as exc:
        logger.error("[VertexSearch] Setup failed: %s", exc)
        return False


def _detect_industry(doc_id: str) -> str:
    mapping = {
        "rbi": "fintech", "sebi": "fintech",
        "pdpb": "saas", "it-act": "saas",
        "gst": "all",
    }
    for key, industry in mapping.items():
        if key in doc_id:
            return industry
    return "all"
