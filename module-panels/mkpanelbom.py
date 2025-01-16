#!/usr/bin/env python3

import sys

from kigadgets.board import Board

pcb = Board.load(sys.argv[1])

def mkfpkey(fp):
    fields = fp.native_obj.GetFieldsText()
    fpname = fields['Footprint'].split(':')[-1]
    # lol
    setattr(fp, 'manufacturer', fields.get('Manufacturer', ''))
    setattr(fp, 'mpn', fields.get('MPN', ''))
    
    if fp.manufacturer != '' and fp.mpn != '':
        return (fpname, fp.manufacturer, fp.mpn)
    return (fpname, fields['Value'])

fpks = {}

for fp in pcb.footprints:
    if fp.native_obj.IsExcludedFromBOM() or fp.value == 'NPTH':
        continue
    key = mkfpkey(fp)
    if key not in fpks:
        fpks[key] = []
    fpks[key].append(fp)

total_placements = 0

print('"Id";"Designator";"Footprint";"Quantity";"Value";"Manufacturer";"MPN"')
for id,k in enumerate(fpks):
    fps = fpks[k]
    total_placements += len(fps)
    alldes = ",".join(fp.reference for fp in fps)
    print(f"{id+1};\"{alldes}\";\"{fps[0].fp_name}\";{len(fps)};\"{fps[0].value}\";\"{fps[0].manufacturer}\";\"{fps[0].mpn}\"")

print(f"{len(fpks)} unique BOM items, with {total_placements} total placements", file=sys.stderr)