from __future__ import annotations

from datetime import date
from decimal import Decimal
from textwrap import wrap


PAGE_WIDTH = 595
PAGE_HEIGHT = 842


def _pdf_text(value: object) -> str:
    text = str(value or "").encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class _Canvas:
    def __init__(self) -> None:
        # PDF pages are transparent unless a background is explicitly painted.
        # Embedded browser viewers can composite that transparency over their
        # dark viewer canvas, making the black contract content appear blank.
        self.commands: list[str] = [
            f"1 1 1 rg 0 0 {PAGE_WIDTH} {PAGE_HEIGHT} re f",
            "0 0 0 rg 0 0 0 RG",
        ]

    def text(self, x: float, y: float, value: object, size: int = 10, bold: bool = False) -> None:
        font = "F2" if bold else "F1"
        self.commands.append(
            f"BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({_pdf_text(value)}) Tj ET"
        )

    def centered(self, y: float, value: object, size: int = 10, bold: bool = False) -> None:
        text = str(value or "")
        approximate_width = len(text) * size * 0.52
        self.text(max(35, (PAGE_WIDTH - approximate_width) / 2), y, text, size, bold)

    def line(self, x1: float, y1: float, x2: float, y2: float, width: float = 0.6) -> None:
        self.commands.append(f"{width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")

    def rect(self, x: float, y: float, width: float, height: float) -> None:
        self.commands.append(f"0.6 w {x:.1f} {y:.1f} {width:.1f} {height:.1f} re S")


def _build_pdf(content: str) -> bytes:
    stream = content.encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    )
    return bytes(pdf)


def generate_contract_pdf(contract, customer, company) -> bytes:
    canvas = _Canvas()
    header_lines = wrap(str(company.name).upper(), width=66) or ["COMPANY"]
    header_y = 800
    for line in header_lines[:2]:
        canvas.centered(header_y, line, 12, True)
        header_y -= 16
    company_contact = " | ".join(filter(None, [company.phone_number, company.email]))
    canvas.centered(header_y - 2, company_contact, 8)
    canvas.centered(header_y - 15, f"Company code: {company.company_code}", 8)
    canvas.line(35, header_y - 27, 560, header_y - 27, 1)

    y = header_y - 48
    canvas.text(35, y, "CUSTOMER SERVICE CONTRACT", 13, True)
    canvas.text(390, y, f"Contract ID: {contract.contract_code}", 8, True)

    y -= 34
    canvas.text(35, y, "CONTACT DETAILS", 9, True)
    canvas.text(315, y, "LOCATION DETAILS", 9, True)
    canvas.line(35, y - 4, 270, y - 4)
    canvas.line(315, y - 4, 560, y - 4)
    details = [
        ("Name", customer.name, "Area", customer.location),
        ("Contact Number", customer.phone_no, "Road", customer.place_id),
        ("Email", customer.email, "Flat No/House No", customer.flat_no or customer.house_no),
    ]
    y -= 24
    for left_label, left_value, right_label, right_value in details:
        canvas.text(35, y, f"{left_label}: {left_value or '-'}", 9)
        canvas.text(315, y, f"{right_label}: {right_value or '-'}", 9)
        y -= 21

    y -= 16
    canvas.text(35, y, "TERMS AGREED", 9, True)
    canvas.text(315, y, "RATE FOR SERVICES", 9, True)
    canvas.line(35, y - 4, 270, y - 4)
    canvas.line(315, y - 4, 560, y - 4)
    y -= 25
    amount = f"UGX {Decimal(contract.agreed_amount):,.0f}"
    terms = [
        ("Agreed Price", amount),
        ("Collection Frequency", contract.pickup_frequency),
        ("Start Date", _date(contract.start_date)),
        ("Expiry Date", _date(contract.expiry_date)),
    ]
    for label, value in terms:
        canvas.text(35, y, f"{label}: {value}", 9)
        y -= 21
    box_y = y + 9
    canvas.rect(315, box_y, 245, 75)
    canvas.line(315, box_y + 50, 560, box_y + 50)
    canvas.line(395, box_y, 395, box_y + 75)
    canvas.text(323, box_y + 58, "Plan", 8, True)
    canvas.text(403, box_y + 58, contract.plan_duration, 8)
    canvas.text(323, box_y + 34, "Frequency", 8, True)
    canvas.text(403, box_y + 34, contract.pickup_frequency, 8)
    canvas.text(323, box_y + 10, "Rate", 8, True)
    canvas.text(403, box_y + 10, amount, 8)

    y -= 25
    canvas.text(35, y, "FOR THE CLIENT", 9, True)
    canvas.text(315, y, f"FOR {company.name.upper()}", 9, True)
    y -= 25
    canvas.text(35, y, "I agree to pay for the services.", 9)
    canvas.text(315, y, "I agree to provide the services.", 9)
    y -= 28
    canvas.text(35, y, f"Name: {customer.name}", 9)
    canvas.text(315, y, f"Name: {company.contact_person}", 9)
    y -= 30
    canvas.text(35, y, "Signature: __________________________", 9)
    canvas.text(315, y, "Signature: __________________________", 9)
    y -= 28
    canvas.text(35, y, f"Collection Frequency: {contract.pickup_frequency}", 9)

    y -= 38
    canvas.text(35, y, f"N.B. {company.name.upper()} WILL", 9, True)
    canvas.line(35, y - 4, 330, y - 4)
    conditions = [
        "Provide refuse bags for each scheduled collection day.",
        "Collect only refuse placed in the bags provided.",
        "Collect refuse from the agreed location and on the agreed days.",
        "Require payment for the service in advance.",
        "Require one month's notice before termination of the contract.",
    ]
    y -= 24
    for index, condition in enumerate(conditions, start=1):
        canvas.text(45, y, f"{index}. {condition}", 8)
        y -= 17

    canvas.line(35, 45, 560, 45)
    canvas.text(35, 30, f"Generated contract: {contract.contract_code}", 7)
    canvas.text(430, 30, f"Created: {_date(contract.created_at.date())}", 7)
    return _build_pdf("\n".join(canvas.commands))


def _date(value: date) -> str:
    return value.strftime("%d %b %Y")
