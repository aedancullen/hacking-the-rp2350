# Copyright (c) 2024 Aedan Cullen
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import pickle

with open(sys.argv[1], "rb") as fh:
    lists = pickle.load(fh)
    if len(lists) == 5:
        delays, widths, up_rates, dump_rates, regdumps = lists
        apinfos = []
    else:
        delays, widths, up_rates, dump_rates, regdumps, apinfos = lists

try:
    GOOD_DUMP = regdumps[0][0]
except:
    GOOD_DUMP = None

for i, regdump in enumerate(regdumps):
    for j, dump_attempt in enumerate(regdump):
        if dump_attempt != GOOD_DUMP:
            print("at delay", delays[i], "attempt", j+1)
            for k in range(len(dump_attempt) // 4):
                print(k, dump_attempt[k*4 : (k+1)*4][::-1].hex())
            input()
