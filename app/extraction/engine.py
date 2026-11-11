
from pathlib import Path
import csv

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from PIL import Image, ImageOps, ImageEnhance
import pytesseract


# =========================================================
# TESSERACT OCR CONFIGURATION
# =========================================================

# Default Windows installation path.
# Change this only if Tesseract is installed elsewhere.

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

if Path(TESSERACT_PATH).exists():
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# =========================================================
# PDF EXTRACTION
# =========================================================

def extract_pdf(file_path):
    """
    Extract selectable text from PDF documents.
    Returns extracted text as a string.
    """

    try:
        reader = PdfReader(file_path)

        if reader.is_encrypted:
            raise ValueError(
                "This PDF is password-protected."
            )

        pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            text = page.extract_text() or ""

            pages.append(
                f"Page {page_number}\n{text}"
            )

        return "\n\n".join(pages).strip()

    except Exception as error:
        raise RuntimeError(
            f"PDF extraction failed: {error}"
        ) from error


# =========================================================
# WORD DOCUMENT EXTRACTION
# =========================================================

def extract_word(file_path):
    """
    Extract paragraphs and tables from DOCX documents.
    """

    try:
        document = Document(file_path)

        content = []

        # Extract paragraphs
        for paragraph in document.paragraphs:

            text = paragraph.text.strip()

            if text:
                content.append(text)

        # Extract tables
        for table_number, table in enumerate(
            document.tables,
            start=1
        ):

            content.append(
                f"\nTable {table_number}:"
            )

            for row in table.rows:

                row_data = [
                    cell.text.strip()
                    for cell in row.cells
                ]

                content.append(
                    " | ".join(row_data)
                )

        return "\n".join(content).strip()

    except Exception as error:
        raise RuntimeError(
            f"Word extraction failed: {error}"
        ) from error


# =========================================================
# EXCEL EXTRACTION
# =========================================================

def extract_excel(file_path):
    """
    Extract data from all worksheets in XLSX files.
    """

    workbook = None

    try:
        workbook = load_workbook(
            file_path,
            read_only=True,
            data_only=True
        )

        content = []

        for sheet in workbook.worksheets:

            content.append(
                f"\nSheet: {sheet.title}"
            )

            for row in sheet.iter_rows(
                values_only=True
            ):

                row_data = [
                    str(value)
                    if value is not None
                    else ""
                    for value in row
                ]

                content.append(
                    " | ".join(row_data)
                )

        return "\n".join(content).strip()

    except Exception as error:
        raise RuntimeError(
            f"Excel extraction failed: {error}"
        ) from error

    finally:
        if workbook is not None:
            workbook.close()


# =========================================================
# CSV EXTRACTION
# =========================================================

def extract_csv(file_path):
    """
    Extract rows from CSV files.
    Supports UTF-8 and Windows encoding.
    """

    content = []

    encodings = [
        "utf-8-sig",
        "cp1252"
    ]

    last_error = None

    for encoding in encodings:

        try:
            with open(
                file_path,
                "r",
                encoding=encoding,
                newline=""
            ) as file:

                reader = csv.reader(file)

                content = []

                for row in reader:

                    content.append(
                        " | ".join(row)
                    )

            return "\n".join(content).strip()

        except UnicodeDecodeError as error:
            last_error = error

    raise RuntimeError(
        f"CSV encoding error: {last_error}"
    )


# =========================================================
# IMAGE OCR EXTRACTION
# =========================================================

def extract_image(file_path):
    """
    Extract text from PNG and JPEG images using Tesseract OCR.
    """

    try:

        image = Image.open(file_path)

        with image:

            # Correct image orientation
            image = ImageOps.exif_transpose(image)

            # Convert to grayscale
            image = image.convert("L")

            # Improve contrast
            image = ImageEnhance.Contrast(
                image
            ).enhance(1.5)

            # OCR processing
            extracted_text = (
                pytesseract.image_to_string(
                    image,
                    lang="eng",
                    config="--psm 3"
                )
            )

            return extracted_text.strip()

    except pytesseract.TesseractNotFoundError as error:

        raise RuntimeError(
            "Tesseract OCR executable not found. "
            "Install Tesseract OCR and configure "
            "TESSERACT_PATH in engine.py."
        ) from error

    except Exception as error:

        raise RuntimeError(
            f"Image OCR extraction failed: {error}"
        ) from error


# =========================================================
# MAIN FILE EXTRACTION FUNCTION
# =========================================================

def extract_file(file_path):
    """
    Detect file type and execute the correct extractor.

    Supported formats:
        PDF
        DOCX
        XLSX
        CSV
        PNG
        JPG
        JPEG

    Always returns a string.
    """

    path = Path(file_path)

    # Check file existence
    if not path.exists():

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    if not path.is_file():

        raise ValueError(
            "The supplied path is not a file."
        )

    extension = path.suffix.lower()

    # Supported extraction functions
    extractors = {

        ".pdf": extract_pdf,

        ".docx": extract_word,

        ".xlsx": extract_excel,

        ".csv": extract_csv,

        ".png": extract_image,

        ".jpg": extract_image,

        ".jpeg": extract_image,

    }

    extractor = extractors.get(extension)

    if extractor is None:

        raise ValueError(
            f"Unsupported file format: {extension}"
        )

    # Execute extraction
    extracted_text = extractor(
        str(path)
    )

    # Ensure string output
    if not isinstance(extracted_text, str):

        raise TypeError(
            "Extraction engine must return text as a string."
        )

    return extracted_text.strip()


# =========================================================
# ENGINE STATUS
# =========================================================

def get_engine_status():
    """
    Return the availability of the extraction components.
    """

    return {

        "pdf": True,

        "word": True,

        "excel": True,

        "csv": True,

        "image_ocr": Path(
            pytesseract.pytesseract.tesseract_cmd
        ).exists(),

        "tesseract_path": (
            pytesseract.pytesseract.tesseract_cmd
        )

    }
