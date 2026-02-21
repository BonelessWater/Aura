from __future__ import annotations

import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiofiles
from fastapi import UploadFile


@asynccontextmanager
async def save_uploads(
    files: list[UploadFile], patient_id: str
) -> AsyncIterator[list[Path]]:
    """
    Save uploaded files to a temp dir, yield their paths, then clean up.

    Usage::

        async with save_uploads(uploaded_files, patient_id) as paths:
            result = some_pipeline(patient_id, pdf_paths=paths)
    """
    tmpdir = Path(tempfile.mkdtemp(prefix=f"aura_{patient_id}_"))
    paths: list[Path] = []
    try:
        for upload in files:
            filename = Path(upload.filename).name if upload.filename else "file"
            dest = tmpdir / filename
            # Handle duplicate filenames
            counter = 1
            while dest.exists():
                dest = tmpdir / f"{dest.stem}_{counter}{dest.suffix}"
                counter += 1
            async with aiofiles.open(dest, "wb") as f:
                content = await upload.read()
                await f.write(content)
            paths.append(dest)
        yield paths
    finally:
        for p in paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            tmpdir.rmdir()
        except OSError:
            pass
