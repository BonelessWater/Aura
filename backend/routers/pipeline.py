from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.config import Settings, get_settings, vector_search_available
from backend.session import get_or_create_session, push_event
from backend.utils.background import create_job, get_job
from backend.utils.file_handling import save_uploads

router = APIRouter()


@router.post("/pipeline/full")
async def full_pipeline(
    patient_id: Annotated[str, Form()],
    symptom_text: Annotated[str, Form()],
    patient_age: Annotated[int, Form()] = 40,
    patient_sex: Annotated[str, Form()] = "F",
    medications: Annotated[str, Form()] = "",
    pdfs: Annotated[list[UploadFile], File()] = [],
    images: Annotated[list[UploadFile], File()] = [],
    settings: Settings = Depends(get_settings),
):
    """
    End-to-end pipeline in a single request.
    Runs: extract → interview → (research if vector search available) → route → translate.
    Dispatched as a background task; use GET /stream/{patient_id} or GET /jobs/{job_id}.
    """
    if not pdfs and not symptom_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Provide at least one PDF or non-empty symptom_text.",
        )

    medication_list = [m.strip() for m in medications.split(",") if m.strip()]

    # Read file bytes now (before the request closes) then write in background.
    pdf_contents: list[tuple[str, bytes]] = []
    for f in pdfs:
        content = await f.read()
        pdf_contents.append((f.filename or "upload.pdf", content))

    image_contents: list[tuple[str, bytes]] = []
    for f in images:
        content = await f.read()
        image_contents.append((f.filename or "image.jpg", content))

    job = create_job(patient_id)
    get_or_create_session(patient_id)

    asyncio.create_task(
        _run_full_pipeline(
            job.job_id,
            patient_id,
            symptom_text,
            patient_age,
            patient_sex,
            medication_list,
            pdf_contents,
            image_contents,
            settings,
        )
    )

    return {"patient_id": patient_id, "job_id": job.job_id, "status": "queued"}


async def _run_full_pipeline(
    job_id: str,
    patient_id: str,
    symptom_text: str,
    patient_age: int,
    patient_sex: str,
    medications: list[str],
    pdf_contents: list[tuple[str, bytes]],
    image_contents: list[tuple[str, bytes]],
    settings: Settings,
):
    import tempfile
    from pathlib import Path

    job = get_job(job_id)
    job.status = "running"
    session = get_or_create_session(patient_id)

    def _emit(phase: str, detail: str = ""):
        push_event(patient_id, {"type": "progress", "phase": phase, "detail": detail})

    try:
        # ── Phase 1: Extract ──────────────────────────────────────────────────
        if pdf_contents:
            _emit("extract", "Saving PDF files")
            tmpdir = Path(tempfile.mkdtemp(prefix=f"aura_{patient_id}_"))
            pdf_paths: list[str] = []
            try:
                for name, data in pdf_contents:
                    p = tmpdir / Path(name).name
                    p.write_bytes(data)
                    pdf_paths.append(str(p))

                _emit("extract", "Running biomarker extraction")
                from nlp.extractor.pipeline import run_extractor

                lab_report = await asyncio.to_thread(
                    run_extractor,
                    patient_id,
                    pdf_paths,
                    patient_age,
                    patient_sex,
                    settings.write_to_databricks,
                )
                session.lab_report = lab_report
                _emit("extract", "Lab report complete")
            finally:
                for p in pdf_paths:
                    try:
                        Path(p).unlink(missing_ok=True)
                    except OSError:
                        pass
                try:
                    tmpdir.rmdir()
                except OSError:
                    pass

        # ── Phase 2: Interview ────────────────────────────────────────────────
        _emit("interview", "Extracting symptom entities")
        img_paths: list[str] = []
        img_tmpdir = Path(tempfile.mkdtemp(prefix=f"aura_{patient_id}_img_"))
        try:
            for name, data in image_contents:
                p = img_tmpdir / Path(name).name
                p.write_bytes(data)
                img_paths.append(str(p))

            from nlp.interviewer.pipeline import run_interviewer

            interview_result = await asyncio.to_thread(
                run_interviewer,
                patient_id,
                symptom_text,
                img_paths,
                [],
            )
            session.interview_result = interview_result
            _emit("interview", "Interview complete")
        finally:
            for p in img_paths:
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                img_tmpdir.rmdir()
            except OSError:
                pass

        # ── Phase 3: Research (optional — skip if no vector backend) ──────────
        if vector_search_available():
            _emit("research", "Running RAG retrieval")
            from nlp.researcher.pipeline import run_researcher

            research_result = await asyncio.to_thread(
                run_researcher,
                patient_id,
                session.lab_report,
                session.interview_result,
                None,
            )
            session.research_result = research_result
            _emit("research", "Research complete")
        else:
            _emit("research", "Skipped — vector search not configured")

        # ── Phase 4: Route ────────────────────────────────────────────────────
        _emit("route", "Scoring cluster alignment and disease candidates")
        from nlp.router.pipeline import run_router

        router_output = await asyncio.to_thread(
            run_router,
            patient_id,
            session.lab_report,
            session.interview_result,
            session.research_result,
            medications,
            patient_age,
            patient_sex,
        )
        session.router_output = router_output
        _emit("route", "Routing complete")

        # ── Phase 5: Translate ────────────────────────────────────────────────
        _emit("translate", "Generating SOAP note and Layman's Compass")
        from nlp.translator.pipeline import run_translator

        translator_output = await asyncio.to_thread(
            run_translator,
            patient_id,
            session.lab_report,
            session.interview_result,
            session.research_result,
            session.router_output,
        )
        session.translator_output = translator_output
        _emit("translate", "Translation complete")

        # ── Done ──────────────────────────────────────────────────────────────
        job.result = {
            "lab_report": session.lab_report.model_dump(mode="json") if session.lab_report else None,
            "interview_result": session.interview_result.model_dump(mode="json") if session.interview_result else None,
            "research_result": session.research_result.model_dump(mode="json") if session.research_result else None,
            "router_output": session.router_output.model_dump(mode="json") if session.router_output else None,
            "translator_output": session.translator_output.model_dump(mode="json") if session.translator_output else None,
        }
        job.status = "done"
        push_event(patient_id, {"type": "done", "job_id": job_id})

    except Exception as exc:
        job.error = str(exc)
        job.status = "error"
        push_event(
            patient_id,
            {"type": "error", "job_id": job_id, "detail": str(exc)},
        )
