#!/usr/bin/env python3

from jinja2 import Environment, PackageLoader
import argparse
import sys
import socket

def render_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', action="store", nargs = 1, default=["serial"])
    parser.add_argument('--board', action="store", nargs = 1, default=["X1P-002-C02"])
    parser.add_argument('--start', action="store", nargs = 1, required=True)
    parser.add_argument('--count', action="store", nargs = 1, required=True)
    parser.add_argument('--file', action="store", nargs = 1)
    parser.add_argument('--print', action="store", nargs = 1)

    args = parser.parse_args()

    serials = [f"{args.board[0]}-{int(args.start[0]) + n:04d}" for n in range(int(args.count[0]))]

    env = Environment(loader=PackageLoader("print_labels", "."))
    zpl = env.get_template(f"{args.template[0]}.zpl_tpl").render(serials = serials)
    
    print(f"generated {len(zpl)} bytes of ZPL for {len(serials)} serials:", file=sys.stderr)
    print(f"  {serials}", file=sys.stderr)
    
    if args.file:
        if args.file[0] == "-":
            print(zpl)
        else:
            with open(args.file[0], 'w') as f:
                f.write(zpl)
    if args.print:
        skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        skt.connect((args.print[0], 9100))
        skt.send(zpl.encode("UTF-8"))
        skt.close()

if __name__ == '__main__':
    render_main()