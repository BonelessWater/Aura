# Databricks notebook source
# MAGIC %md
# MAGIC # Build PubMed Vector Search Index
# MAGIC
# MAGIC Processes 90K PubMed OA articles from the volume into a searchable
# MAGIC vector index for the Aura RAG pipeline.
# MAGIC
# MAGIC **Steps:**
# MAGIC 1. Extract JATS XML from tar.gz files in the volume
# MAGIC 2. Parse article metadata (DOI, journal, year, sections)
# MAGIC 3. Chunk article text into ~300-word passages
# MAGIC 4. Write to `workspace.aura.pubmed_chunks` Delta table
# MAGIC 5. Create Vector Search endpoint + Delta Sync Index with managed embeddings

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Parse articles from volume

# COMMAND ----------

import io
import re
import hashlib
import tarfile
import xml.etree.ElementTree as ET
from typing import Optional

def parse_jats_xml(xml_content: str) -> Optional[dict]:
    """Parse a JATS XML article and extract metadata + body text."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return None

    ns = {"xlink": "http://www.w3.org/1999/xlink"}

    # DOI
    doi = None
    for aid in root.findall(".//article-id"):
        if aid.get("pub-id-type") == "doi":
            doi = aid.text
            break

    # PMC ID
    pmc_id = None
    for aid in root.findall(".//article-id"):
        if aid.get("pub-id-type") == "pmc":
            pmc_id = aid.text
            break

    # Journal
    journal = None
    jt = root.find(".//journal-title")
    if jt is not None and jt.text:
        journal = jt.text.strip()

    # Year
    year = None
    for pd in root.findall(".//pub-date"):
        y = pd.find("year")
        if y is not None and y.text:
            year = int(y.text)
            break

    # Title
    title = None
    t = root.find(".//article-title")
    if t is not None:
        title = "".join(t.itertext()).strip()

    # Abstract
    abstract_parts = []
    for ab in root.findall(".//abstract"):
        abstract_parts.append("".join(ab.itertext()).strip())
    abstract = " ".join(abstract_parts)

    # Body sections
    sections = []
    for sec in root.findall(".//body//sec"):
        sec_title_el = sec.find("title")
        sec_title = sec_title_el.text.strip() if sec_title_el is not None and sec_title_el.text else "Body"
        # Get all paragraph text in this section (not nested secs)
        paras = []
        for p in sec.findall("p"):
            paras.append("".join(p.itertext()).strip())
        if paras:
            sections.append({"title": sec_title, "text": " ".join(paras)})

    # If no sections found, try to get all body text
    if not sections:
        body = root.find(".//body")
        if body is not None:
            body_text = "".join(body.itertext()).strip()
            if body_text:
                sections.append({"title": "Body", "text": body_text})

    return {
        "doi": doi,
        "pmc_id": pmc_id,
        "journal": journal,
        "year": year,
        "title": title,
        "abstract": abstract,
        "sections": sections,
    }


def chunk_text(text: str, max_words: int = 300, overlap_words: int = 50) -> list[str]:
    """Split text into overlapping chunks of ~max_words."""
    words = text.split()
    if len(words) <= max_words:
        return [text] if len(words) > 20 else []

    chunks = []
    start = 0
    while start < len(words):
        end = start + max_words
        chunk = " ".join(words[start:end])
        if len(chunk.split()) > 20:  # skip tiny chunks
            chunks.append(chunk)
        start += max_words - overlap_words
    return chunks


def process_tar_gz(file_path: str, file_content: bytes) -> list[dict]:
    """Process a single tar.gz article file into chunks."""
    rows = []
    try:
        with tarfile.open(fileobj=io.BytesIO(file_content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.name.endswith((".nxml", ".xml")):
                    continue
                f = tar.extractfile(member)
                if f is None:
                    continue
                xml_content = f.read().decode("utf-8", errors="replace")
                article = parse_jats_xml(xml_content)
                if article is None:
                    continue

                doi = article["doi"]
                pmc_id = article["pmc_id"]
                journal = article["journal"]
                year = article["year"]

                # Chunk abstract
                if article["abstract"]:
                    for i, chunk in enumerate(chunk_text(article["abstract"])):
                        chunk_id = hashlib.md5(
                            f"{pmc_id}_abstract_{i}".encode()
                        ).hexdigest()
                        rows.append({
                            "chunk_id": chunk_id,
                            "doi": doi,
                            "pmc_id": pmc_id,
                            "journal": journal,
                            "year": year,
                            "section": "Abstract",
                            "text": chunk,
                        })

                # Chunk body sections
                for sec in article["sections"]:
                    for i, chunk in enumerate(chunk_text(sec["text"])):
                        chunk_id = hashlib.md5(
                            f"{pmc_id}_{sec['title']}_{i}".encode()
                        ).hexdigest()
                        rows.append({
                            "chunk_id": chunk_id,
                            "doi": doi,
                            "pmc_id": pmc_id,
                            "journal": journal,
                            "year": year,
                            "section": sec["title"][:100],
                            "text": chunk,
                        })
    except Exception:
        pass  # skip corrupt files
    return rows

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Process all articles with Spark

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from pyspark.sql.functions import col

# Schema for the chunks table
chunk_schema = StructType([
    StructField("chunk_id", StringType(), False),
    StructField("doi", StringType(), True),
    StructField("pmc_id", StringType(), True),
    StructField("journal", StringType(), True),
    StructField("year", IntegerType(), True),
    StructField("section", StringType(), True),
    StructField("text", StringType(), False),
])

# Read all tar.gz files as binary
volume_path = "/Volumes/workspace/aura/pubmed_oa/articles/"
binary_df = spark.read.format("binaryFile").load(volume_path + "*.tar.gz")

print(f"Found {binary_df.count()} article files")

# COMMAND ----------

# Process in batches using Spark UDF
import pyspark.sql.functions as F
from pyspark.sql.types import ArrayType

@F.udf(returnType=ArrayType(chunk_schema))
def extract_chunks_udf(path, content):
    return process_tar_gz(path, bytes(content))

# Apply the UDF to extract chunks
chunks_df = (
    binary_df
    .withColumn("chunks", extract_chunks_udf(col("path"), col("content")))
    .select(F.explode("chunks").alias("chunk"))
    .select("chunk.*")
)

# Write to Delta table
(
    chunks_df
    .write
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable("workspace.aura.pubmed_chunks")
)

chunk_count = spark.table("workspace.aura.pubmed_chunks").count()
print(f"Written {chunk_count:,} chunks to workspace.aura.pubmed_chunks")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create Vector Search Index
# MAGIC
# MAGIC Uses Databricks Managed Embeddings (Delta Sync Index).
# MAGIC Databricks auto-computes embeddings using a built-in model.

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

VS_ENDPOINT = "aura-vs-endpoint"
VS_INDEX_NAME = "workspace.aura.pubmed_vs_index"
SOURCE_TABLE = "workspace.aura.pubmed_chunks"

vsc = VectorSearchClient()

# Create endpoint (if not exists)
try:
    vsc.create_endpoint(name=VS_ENDPOINT, endpoint_type="STANDARD")
    print(f"Created VS endpoint: {VS_ENDPOINT}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"VS endpoint '{VS_ENDPOINT}' already exists")
    else:
        print(f"Endpoint error: {e}")

# COMMAND ----------

# Create Delta Sync Index with managed embeddings
# Databricks will auto-embed the 'text' column
try:
    index = vsc.create_delta_sync_index(
        endpoint_name=VS_ENDPOINT,
        index_name=VS_INDEX_NAME,
        source_table_name=SOURCE_TABLE,
        pipeline_type="TRIGGERED",
        primary_key="chunk_id",
        embedding_source_column="text",
        embedding_model_endpoint_name="databricks-bge-large-en",
    )
    print(f"Created VS index: {VS_INDEX_NAME}")
    print("Index is syncing. This may take 30-60 minutes for 90K articles.")
    print("Check status in the Databricks UI under 'Vector Search'.")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"VS index '{VS_INDEX_NAME}' already exists")
        # Trigger a sync
        try:
            index = vsc.get_index(VS_ENDPOINT, VS_INDEX_NAME)
            index.sync()
            print("Triggered index sync")
        except Exception as sync_e:
            print(f"Sync error: {sync_e}")
    else:
        print(f"Index creation error: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Verify
# MAGIC
# MAGIC Run this cell after the index sync is complete (~30-60 min).

# COMMAND ----------

# Test a search query
try:
    index = vsc.get_index(VS_ENDPOINT, VS_INDEX_NAME)
    results = index.similarity_search(
        query_text="rheumatoid arthritis joint inflammation biomarkers",
        columns=["chunk_id", "doi", "journal", "year", "section", "text"],
        num_results=3,
    )
    print("Test search results:")
    for row in results.get("result", {}).get("data_array", []):
        print(f"  DOI: {row[1]}, Section: {row[4]}")
        print(f"  Text: {row[5][:150]}...")
        print()
except Exception as e:
    print(f"Search test error (index may still be syncing): {e}")
