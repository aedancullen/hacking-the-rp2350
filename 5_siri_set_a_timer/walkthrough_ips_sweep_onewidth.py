# Copyright (c) 2024 Aedan Cullen
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import pickle

with open(sys.argv[1], "rb") as fh:
    delays, widths, up_rates, dump_rates, regdumps = pickle.load(fh)

GOOD_DUMP = regdumps[0][0]

for i, regdump in enumerate(regdumps):
    for j, dump_attempt in enumerate(regdump):
        if dump_attempt != GOOD_DUMP:
            print("at delay", delays[i], "attempt", j+1)
            for k in range(len(dump_attempt) // 4):
                print(k, dump_attempt[k*4 : (k+1)*4].hex())
            input()
