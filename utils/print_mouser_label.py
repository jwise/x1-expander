#!/usr/bin/env python3

from simple_zpl2 import ZPLDocument, DataMatrix_Barcode
from PIL import Image
from collections import namedtuple
import datetime

def mk_product_label(zdoc, xoff = 10, yoff = 10, flip = False, mpn = "X1P-800", rev = "A01", coo = "CN", desc = "X1Plus Expander Housing", date = None):
    orientation = 'I' if flip else 'N'

    def origin(x, y):
        mul = -1 if flip else 1
        zdoc.add_field_origin(xoff + x * mul, yoff + y * mul, '1' if flip else '0')
    
    def put_box(x, y, w, h, sz):
        if flip:
            origin(x, y + h)
        else:
            origin(x, y)
        zdoc.add_graphic_box(w, h, sz)
    
    def put_text(x, y, font, h, text):
        if flip:
            origin(x, y+h)
        else:
            origin(x, y)
        zdoc.add_font(font, orientation, h)
        zdoc.add_field_data(text)

    #zdoc.add_zpl_raw(f"^FW{orientation},{orientation}")
    xpos = 0
    ypos = 0
    put_box(xpos, ypos, 540, 85, 3)
    put_box(xpos, ypos, 77, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'MPN')
    put_text(xpos + 100, ypos + 10, 'D', 72, mpn)
    
    ypos += 82
    put_box(xpos, ypos, 540, 60, 3)
    put_box(xpos, ypos, 84, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'DESC')
    put_text(xpos + 100, ypos + 12, '0', 42, desc)
    
    ypos += 57
    put_box(xpos, ypos, 540, 65, 3)
    put_box(xpos, ypos, 75, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'MFR')
    logo = Image.open('accelerated-tech-label.png')
    if flip:
        logo = logo.rotate(180)
        origin(xpos + 100 + logo.size[0], ypos + 10 + logo.size[1])
    else:
        origin(xpos + 100, ypos + 10)
    zdoc.add_graphic_field(logo, logo.size[0], logo.size[1], 'A')
    
    ypos += 62
    put_box(xpos, ypos, 120, 60, 3)
    put_box(xpos, ypos, 67, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'QTY')
    put_text(xpos + 80, ypos + 10, '0', 42, '1')
    
    xpos += 117
    put_box(xpos, ypos, 180, 60, 3)
    put_box(xpos, ypos, 67, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'REV')
    put_text(xpos + 80, ypos + 14, 'D', 36, rev)
    
    xpos += 177
    put_box(xpos, ypos, 150, 60, 3)
    put_box(xpos, ypos, 67, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'CoO')
    put_text(xpos + 80, ypos + 10, '0', 42, coo)
    
    if date is None:
        date = datetime.date.today().strftime("%y%W")
    xpos += 147
    put_box(xpos, ypos, 301, 60, 3)
    put_box(xpos, ypos, 81, 42, 2)
    put_text(xpos + 10, ypos + 10, '0', 30, 'DATE')
    put_text(xpos + 94, ypos + 14, 'D', 36, date)
    
    _SOT = "[)>"
    _RS = "\x1E"
    _GS = "\x1D"
    _EOT = "\x04"
    lot_code = "0001"
    qty = "1"
    bcode_data = f"{_SOT}{_RS}06{_GS}1P{mpn}{_GS}2P{rev}{_GS}1T{lot_code}{_GS}10D{date}{_GS}4L{coo}{_GS}Q{qty}{_GS}{_RS}{_EOT}"

    if flip:
        origin(550, 32 * 6)
    else:
        origin(550, 0)
    zdoc.add_barcode(DataMatrix_Barcode(bcode_data, 'N', 6, 200, 32, 32))

    put_text(115, 285, '0', 37, 'https://accelerated.tech/expander/')

    zdoc.add_zpl_raw(f"^FWN,N")

Product = namedtuple('Product', [ 'params', 'fliptop' ])

PRODUCTS = {
    'X1P-800': Product(fliptop = True, params = {
        'mpn': 'X1P-800',
        'rev': 'A02',
        'coo': 'CN',
        'desc': 'Mounting Bracket & Enclo',
    })
}

def zdoc_for_product(product):
    product = PRODUCTS[product]

    zdoc = ZPLDocument()
    if product.fliptop:
        mk_product_label(zdoc, xoff = 751, yoff = int(1.25 * 300) - 35, flip = True, **product.params)
    else:
        mk_product_label(zdoc, xoff = 9, yoff = 30, **product.params)
    mk_product_label(zdoc, xoff = 9, yoff = int(1.25 * 300) + 40, **product.params)
    zdoc.add_field_origin(0, 375)
    zdoc.add_graphic_box(800, 3, 3)
    
    return zdoc

def show_zdoc(zdoc):
    import io
    png = zdoc.render_png(label_width=2.5, label_height=2.5, dpmm=12)
    fake_file = io.BytesIO(png)
    img = Image.open(fake_file)
    img.show()

if __name__ == '__main__':
    import argparse
    import socket

    parser = argparse.ArgumentParser()
    parser.add_argument('product', action="store", nargs = 1)
    parser.add_argument('--copies', action="store", nargs = 1, default = ['1'])
    parser.add_argument('--show', action="store_true")
    parser.add_argument('--file', action="store", nargs = 1)
    parser.add_argument('--print', action="store", nargs = 1)
    args = parser.parse_args()
    
    zdoc = zdoc_for_product(args.product[0])
    zdoc.add_print_quantity(int(args.copies[0]))
    if args.show:
        show_zdoc(zdoc)
    if args.file:
        if args.file[0] == "-":
            print(zdoc.zpl_text)
        else:
            with open(args.file[0], 'w') as f:
                f.write(zdoc.zpl_text)
    if args.print:
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.connect((args.print[0], 9100))
        skt.send(zdoc.zpl_text.encode("UTF-8"))
        skt.close()

