from .payment_information import PaymentInformation
import qrcode
from io import BytesIO


class QRBill:
    def __init__(self, payment_information: PaymentInformation):
        self.payment_information = payment_information

    def generate_qr_string(self) -> str:
        pi = self.payment_information
        lines = [
            "SPC", "0200", "1",
            pi.iban,
            pi.creditor.name,
            pi.creditor.street,
            pi.creditor.house_no,
            pi.creditor.postal_code,
            pi.creditor.city,
            pi.creditor.country,
            "", "", "", "", "", "",  # keine alternative Adresse
            pi.currency,
            f"{pi.amount:.2f}",
            "", "", "", "", "", "",  # keine Zahleradresse
            pi.reference or "",
            pi.unstructured_message or "",
            "EPD"
        ]
        return "\n".join(lines)

    def as_image(self, buffer: BytesIO):
        qr = qrcode.QRCode(version=15, box_size=3, border=2)
        qr.add_data(self.generate_qr_string())
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        img.save(buffer, format="PNG")

