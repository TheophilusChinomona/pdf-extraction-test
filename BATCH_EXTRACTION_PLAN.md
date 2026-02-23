# 🚀 Batch Extraction Plan: 10,000 Exam Papers

**Target:** Process 10,000 PDF Exam Papers + Memos.
**Cost Target:** ~$15.00 (Gemini 1.5 Flash / 2.0 Flash via Batch API).
**Quality Target:** 100% Text/Diagram fidelity.

## 1. The "Chunking" Strategy (Context Management)
To avoid timeouts and hallucinations on 12-20 page documents, we split every PDF into logical chunks.

*   **Chunk 1 (Pages 1-5):** Usually Section A (MCQs) + Start of B.
*   **Chunk 2 (Pages 6-10):** Section B + Start of C.
*   **Chunk 3 (Pages 11-End):** Section C + Diagrams + Information Sheets.

**Why:**
*   **Reliability:** Smaller context = higher accuracy.
*   **Parallelism:** Process chunks simultaneously.
*   **Cost:** Batch API is 50% cheaper.

## 2. The Pipeline Architecture

### Phase 1: Ingest & Pre-process
1.  **Scan:** List all PDFs in the source bucket/folder.
2.  **Split:** Use `pdf2image` (or PyMuPDF) to split PDFs into 5-page image batches.
3.  **Upload:** Upload these image batches to Gemini File API (temporarily) or encode as base64 in the request (if size permits < 20MB). *Recommendation: File API is cleaner for 10k docs.*

### Phase 2: Batch Submission (Async)
1.  **Create Requests:** Generate a JSONL file where each line is a request:
    *   `model`: `gemini-1.5-flash` or `gemini-2.0-flash`
    *   `input`: `[Prompt, Image1, Image2, Image3, Image4, Image5]`
    *   `output_schema`: Enforce JSON schema.
2.  **Submit Job:** Send the JSONL to `google.generativeai.batch.create_job()`.
3.  **Wait:** Jobs complete in < 24 hours (usually < 30 mins).

### Phase 3: Post-process & Merge
1.  **Download Results:** Fetch the JSON output for each chunk.
2.  **Merge Logic:**
    *   Read `Chunk1.json` -> Extract `groups[]`.
    *   Read `Chunk2.json` -> Extract `groups[]`.
    *   Concatenate: `Final_Groups = Chunk1_Groups + Chunk2_Groups + ...`
    *   Deduplicate: Ensure questions aren't repeated at split boundaries (check IDs).
3.  **Validate:** Check total marks (sum of question marks == 150?).

### Phase 4: Database Load
1.  **Target:** Supabase (PostgreSQL).
2.  **Schema:**
    *   `exam_papers` (id, subject, year, session, total_marks)
    *   `questions` (id, paper_id, section, question_number, text, marks, options_json)
    *   `memos` (id, question_id, answer_text, marker_notes)
3.  **Upsert:** Insert the merged JSON into these tables.

## 3. Worker Script Logic (Python)

```python
def process_batch(pdf_files):
    # 1. Split PDFs
    chunks = split_pdfs(pdf_files)
    
    # 2. Upload to Gemini File API
    file_uris = upload_files(chunks)
    
    # 3. Create Batch Job
    job = create_batch_job(file_uris, prompt="EXTRACT_QUESTIONS")
    
    # 4. Poll
    while job.state != "COMPLETED":
        sleep(60)
        
    # 5. Merge & Save
    results = download_results(job)
    final_json = merge_chunks(results)
    save_to_db(final_json)
```

## 4. Cost Estimation (Revised)
*   **Input:** 10k docs * 15 pages * 258 tokens/image = ~38M tokens.
*   **Output:** 10k docs * 4k tokens (JSON) = ~40M tokens.
*   **Gemini 1.5 Flash Batch Pricing:**
    *   Input: Free (up to limit) or $0.0375/1M = ~$1.50
    *   Output: $0.15/1M = ~$6.00
    *   **Total: < $10.00**

## 5. Next Steps
1.  **Set up GCS Bucket:** For holding the split images.
2.  **Write the Splitter Script:** Python script to chunk PDFs.
3.  **Write the Batch Submitter:** Python script to create JSONL and call API.
4.  **Run Pilot:** 100 docs.
5.  **Run Full:** 10,000 docs.
