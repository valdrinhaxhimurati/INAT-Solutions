import io
import qrcode
import qrcode.image.svg
from pathlib import Path
from typing import Optional, Union
from bs4 import BeautifulSoup

from swissqr import QRData


class SwissQR:

    qrfactory = qrcode.image.svg.SvgPathFillImage
    correction = qrcode.ERROR_CORRECT_M
    qrsize = 46
    crosssize = 7

    def __init__(self, data: QRData):
        self.data: QRData = data
        self.soup: Optional[BeautifulSoup] = None

    def _make_soup(self):
        qr = qrcode.QRCode(
            version=None,  # Determine size automatically
            error_correction=SwissQR.correction,
            box_size=10,
            border=0
        )
        qr.add_data(str(self.data))
        vec = qr.make_image(fill_color="black", back_color="white", image_factory=qrcode.image.svg.SvgPathFillImage)
        buf = io.BytesIO()
        vec.save(buf)
        tag = buf.getvalue().decode()
        self.soup = BeautifulSoup(tag, "lxml-xml")

    def _adjust_size(self):
        self.soup.find("svg")["width"] = "{}mm".format(SwissQR.qrsize)
        self.soup.find("svg")["height"] = "{}mm".format(SwissQR.qrsize)

    def _add_cross(self):
        viewbox = self.soup.find("svg")["viewBox"]
        qsize = int(viewbox.split(" ")[2])
        csize = (qsize/SwissQR.qrsize) * SwissQR.crosssize
        coffset = (qsize - csize) / 2
        stroke_width = csize / 12
        style = "fill:rgb(0,0,0);stroke-width:{};stroke:rgb(255,255,255)".format(stroke_width)
        base = self.soup.new_tag("rect")
        base["x"] = coffset
        base["y"] = coffset
        base["width"] = csize
        base["height"] = csize
        base["style"] = style
        self.soup.find("svg").append(base)
        style = "fill:rgb(255,255,255);"
        barwidth = csize / 5.5
        barlength = csize * 0.6
        hbar_x = (qsize - barlength) / 2
        hbar_y = (qsize - barwidth) / 2
        hbar = self.soup.new_tag("rect")
        hbar["x"] = hbar_x
        hbar["y"] = hbar_y
        hbar["width"] = barlength
        hbar["height"] = barwidth
        hbar["style"] = style
        self.soup.find("svg").append(hbar)
        vbar = self.soup.new_tag("rect")
        vbar["x"] = hbar_y
        vbar["y"] = hbar_x
        vbar["width"] = barwidth
        vbar["height"] = barlength
        vbar["style"] = style
        self.soup.find("svg").append(vbar)

    def _svg_code(self) -> str:
        self._make_soup()
        self._adjust_size()
        self._add_cross()
        return str(self.soup)

    def get_markup(self) -> str:
        return self._svg_code().splitlines(keepends=False)[1]

    def save(self, path: Union[str, Path]):
        if not isinstance(path, Path):
            path = Path(path)
        with path.open('w') as f:
            f.write(self._svg_code())
