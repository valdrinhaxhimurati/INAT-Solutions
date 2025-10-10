import unittest
import pathlib
import uuid
import tempfile
from iso4217 import Currency
from swissqr import PaymentParty, QRData, SwissQR


class TestNoException(unittest.TestCase):

    def test_get_markup(self):
        p = PaymentParty(
            name="Hambone Fakenamington",
            street="Madeup Street",
            street_no="1",
            zipcode="9999",
            city="Madeup Town",
            country="CH"
        )
        d = QRData(
            iban="CH9300762011623852957",
            creditor=p,
            amount=5.0,
            currency=Currency.chf,
            message="Have a beer!"
        )
        q = SwissQR(d)
        markup = q.get_markup()
        self.assertGreater(len(markup), 100)

    def test_save_svg(self):
        p = PaymentParty(
            name="Hambone Fakenamington",
            street="Madeup Street",
            street_no="1",
            zipcode="9999",
            city="Madeup Town",
            country="CH"
        )
        d = QRData(
            iban="CH9300762011623852957",
            creditor=p,
            amount=5.0,
            currency=Currency.chf,
            message="Have a beer!"
        )
        q = SwissQR(d)
        path = pathlib.Path(f"{tempfile.gettempdir()}/{str(uuid.uuid4())}.svg")
        q.save(path)
        self.assertTrue(path.is_file())
        path.unlink()
