"""Build only fictional TCGplayer-shaped PDFs; never load a customer order."""
from pathlib import Path
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent / 'generated'
OID = 'TEST0001-ABCDEF-12345'
OTHER = 'TEST0002-ABCDEF-12345'


def make_pdf(path, oid=OID, pages=1, layout='default', page_numbers=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(path), pagesize=(612, 792), invariant=True)
    document.setTitle('Fictional packing slip test fixture')
    document.setAuthor('TCGplayer Print Both test suite')
    for index in range(pages):
        number = page_numbers[index] if page_numbers else index + 1
        document.setFont('Helvetica', 10)
        document.drawString(30, 755, 'Order Number: ' + oid)
        document.drawString(470, 755, f'Page {number} of {pages}')
        if number == 1:
            if layout == 'default':
                document.drawString(30, 720, 'Ship To:')
                document.drawString(30, 704, 'Example Customer')
                document.drawString(30, 690, '123 Example Street')
                document.drawString(30, 676, 'Example City, VA 00000')
                document.drawString(30, 660, 'Order Details')
            elif layout == 'shipping':
                document.drawString(30, 610, 'Shipping Address:')
                document.drawString(30, 594, 'Example Customer')
                document.drawString(30, 580, '123 Example Street')
                document.drawString(30, 566, 'Example City, VA 00000')
            elif layout == 'window':
                document.drawString(95, 630, 'Example Customer')
                document.drawString(95, 616, '123 Example Street')
                document.drawString(95, 602, 'Example City, VA 00000')
                document.drawString(30, 545, 'Fold Line')
        y = 475
        for item in range(24):
            document.drawString(30, y, f'{index * 24 + item + 1}. Example Trading Card | Near Mint | Quantity 1')
            y -= 15
        document.showPage()
    document.save()
    return path


def ensure_fixtures():
    make_pdf(ROOT / 'native-default.pdf')
    make_pdf(ROOT / 'other-order.pdf', OTHER)
    make_pdf(ROOT / 'native-multiple.pdf', pages=3)
    make_pdf(ROOT / 'native-shipping.pdf', layout='shipping')
    make_pdf(ROOT / 'native-window.pdf', layout='window')
    return ROOT


if __name__ == '__main__':
    print('Generated fictional fixtures:', ensure_fixtures())
