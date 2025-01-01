# Copyright (c) 2024 Aedan Cullen
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import bson

with open(sys.argv[1], "rb") as fh:
    d = bson.loads(fh.read())
if not "apinfos" in d.keys():
    d["apinfos"] = []

try:
    GOOD_DUMP = d["regdumps"][0][0]
except:
    GOOD_DUMP = None

for i, regdump in enumerate(d["regdumps"]):
    for j, dump_attempt in enumerate(regdump):
        if dump_attempt != GOOD_DUMP:
            print("at delay", d["delays"][i], "attempt", j+1)
            for k in range(len(dump_attempt) // 4):
                print(k, dump_attempt[k*4 : (k+1)*4][::-1].hex())
            input()
