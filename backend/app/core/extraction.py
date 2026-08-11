"""Download resume files and extract text + embedded URLs.

Handles Google Docs / Google Drive / direct URLs, uses pdfplumber with a
PyMuPDF fallback, and an optional Tesseract OCR fallback for scanned PDFs
and image files. Ported & consolidated from the Streamlit analyzer and the
DSA Extractor's pdf_service.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Tuple
from urllib.parse import urlparse, urlunparse

import fitz  # PyMuPDF
import pdfplumber
import requests

from ..config import get_settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_TIMEOUT = 60

# Lazily-initialised OCR availability flag.
_ocr_checked = False
_ocr_available = False


def is_ocr_available() -> bool:
    global _ocr_checked, _ocr_available
    if _ocr_checked:
        return _ocr_available
    _ocr_checked = True
    settings = get_settings()
    if not settings.enable_ocr:
        _ocr_available = False
        return False
    try:
        import pytesseract

        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        pytesseract.get_tesseract_version()
        _ocr_available = True
    except Exception:
        _ocr_available = False
    return _ocr_available


def download_and_identify_file(file_url: str, output_path: str) -> Tuple[bool, str, str]:
    """Download a file and identify its type by header bytes.

    Returns (success, message_or_path, file_type) where file_type is one of
    'pdf' | 'png' | 'jpeg' | 'unsupported' | 'error'.
    """
    try:
        parsed = urlparse(file_url)
        is_gdoc = "docs.google.com" in parsed.netloc and "/document/" in parsed.path
        is_gdrive = "drive.google.com" in parsed.netloc and (
            "open" in parsed.path or "file" in parsed.path or "/d/" in parsed.path
        )

        if is_gdoc:
            doc_id = parsed.path.split("/d/")[1].split("/")[0]
            parts = list(parsed)
            parts[2] = f"/document/d/{doc_id}/export"
            parts[4] = "format=pdf"
            pdf_url = urlunparse(parts)
            resp = requests.get(pdf_url, headers=_HEADERS, stream=True, timeout=_TIMEOUT)
            resp.raise_for_status()
            _write_stream(resp, output_path)

        elif is_gdrive:
            file_id = None
            if "id=" in parsed.query:
                file_id = parsed.query.split("id=")[1].split("&")[0]
            elif "/d/" in parsed.path:
                file_id = parsed.path.split("/d/")[1].split("/")[0]
            if not file_id:
                raise ValueError("Could not extract file ID from Google Drive URL")

            export_url = f"https://docs.google.com/document/d/{file_id}/export?format=pdf"
            try:
                resp = requests.get(export_url, headers=_HEADERS, stream=True, timeout=_TIMEOUT)
                resp.raise_for_status()
                _write_stream(resp, output_path)
                with open(output_path, "rb") as fh:
                    if not fh.read(5).startswith(b"%PDF"):
                        raise ValueError("On-the-fly conversion did not yield a PDF.")
            except (requests.RequestException, ValueError) as exc:
                logger.warning("GDrive export failed (%s); falling back to direct download.", exc)
                session = requests.Session()
                session.headers.update(_HEADERS)
                url = "https://docs.google.com/uc?export=download"
                resp = session.get(url, params={"id": file_id}, stream=True, timeout=_TIMEOUT)
                token = next(
                    (v for k, v in resp.cookies.items() if k.startswith("download_warning")),
                    None,
                )
                if token:
                    resp = session.get(
                        url, params={"id": file_id, "confirm": token},
                        stream=True, timeout=_TIMEOUT,
                    )
                resp.raise_for_status()
                _write_stream(resp, output_path)
        else:
            resp = requests.get(
                file_url, headers=_HEADERS, stream=True, timeout=_TIMEOUT, allow_redirects=True
            )
            resp.raise_for_status()
            _write_stream(resp, output_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise ValueError("Downloaded file is empty.")

        with open(output_path, "rb") as fh:
            header = fh.read(8)
        if header.startswith(b"%PDF"):
            file_type = "pdf"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            file_type = "png"
        elif header.startswith(b"\xff\xd8\xff"):
            file_type = "jpeg"
        else:
            file_type = "unsupported"

        return True, output_path, file_type

    except requests.RequestException as exc:
        return False, f"Download failed: {exc}", "error"
    except ValueError as exc:
        return False, f"Invalid file or URL: {exc}", "error"
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected download error: {exc}", "error"


def _write_stream(resp: requests.Response, output_path: str) -> None:
    with open(output_path, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                fh.write(chunk)


def _extract_urls_from_annotations(pdf_path: str) -> list[str]:
    urls: list[str] = []
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            for link in page.get_links():
                if link.get("uri"):
                    urls.append(link["uri"])
        doc.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Annotation URL extraction failed for %s: %s", pdf_path, exc)
    return urls


def extract_text_and_urls_from_pdf(pdf_path: str) -> Tuple[str, list[str]]:
    """Extract text (pdfplumber -> fitz -> OCR) and embedded hyperlinks."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed for %s: %s", pdf_path, exc)

    if not text.strip():
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("fitz text extraction failed for %s: %s", pdf_path, exc)

    if not text.strip() and is_ocr_available():
        try:
            import pytesseract
            from PIL import Image

            doc = fitz.open(pdf_path)
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text += pytesseract.image_to_string(img) + "\n"
            doc.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("OCR extraction failed for %s: %s", pdf_path, exc)

    urls = list(set(_extract_urls_from_annotations(pdf_path) + _urls_from_text(text)))
    return text, urls


def extract_text_from_image(image_path: str) -> Tuple[str, list[str]]:
    if not is_ocr_available():
        return "", []
    try:
        import pytesseract
        from PIL import Image

        text = pytesseract.image_to_string(Image.open(image_path))
        return text, _urls_from_text(text)
    except Exception as exc:  # noqa: BLE001
        logger.error("OCR on image %s failed: %s", image_path, exc)
        return "", []


def _urls_from_text(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)]+", text or "")


def fetch_resume(file_url: str) -> Tuple[str, list[str]]:
    """Download + extract. Returns (text, links). Raises ValueError on failure."""
    fd, tmp_path = tempfile.mkstemp(suffix=".tmp")
    os.close(fd)
    try:
        ok, msg, file_type = download_and_identify_file(file_url, tmp_path)
        if not ok:
            raise ValueError(msg)
        if file_type == "pdf":
            return extract_text_and_urls_from_pdf(tmp_path)
        if file_type in ("png", "jpeg"):
            return extract_text_from_image(tmp_path)
        raise ValueError("Unsupported file type (not a PDF or image).")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
