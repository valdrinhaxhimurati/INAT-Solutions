# swissqr

Python lib to generate the QR code of Swiss QR bills. Check [here](https://www.six-group.com/en/products-services/banking-services/billing-and-payments/qr-bill.html) for more details on QR bills.

**Beware:** This library is not well tested, use at your own risk!

## Quickstart:

```python
import pathlib
from iso4217 import Currency
from swissqr import PaymentParty, QRData, SwissQR

# Create a PaymentParty object for the payment receiver
p = PaymentParty(
    name="Hambone Fakenamington",
    street="Madeup Street",
    street_no="1",
    zipcode="9999",
    city="Madeup Town",
    country="CH"
)

# Create QR code data model
d = QRData(
    iban="CH9300762011623852957",
    creditor=p,
    amount=5.0,
    currency=Currency.chf,
    message="Have a beer!"
)

# Create QR code object
q = SwissQR(d)

# Get QR code svg as a string
markup = q.get_markup()

# Save QR code to a file
p = pathlib.Path("/tmp/qr.svg")
q.save(p)
```
