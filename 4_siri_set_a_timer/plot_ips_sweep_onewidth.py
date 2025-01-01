# Copyright (c) 2024 Aedan Cullen
# SPDX-License-Identifier: GPL-3.0-or-later

BGCOLOR = "#000000"

AXCOLOR = "#fef2ff"
AXFONT = "Space Mono"

import sys
import bson
import struct
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

FIELD_KEYS = []
FIELD_IDXS = []
FIELD_MASKS = []

for i in range(64):
    FIELD_KEYS.append(f"+0x{i*4:03X}" + f"SW_LOCK{i} ".rjust(15))
    FIELD_IDXS.append(i*4)
    FIELD_MASKS.append(0xffffffff)

for i in range(8):
    FIELD_KEYS.append(f"+0x148" + f"CRITICAL[{i}] ".rjust(15))
    FIELD_IDXS.append(64*4)
    FIELD_MASKS.append(0b1 << i)

for i in range(8):
    FIELD_KEYS.append(f"+0x14C" + f"KEY_VALID[{i}] ".rjust(15))
    FIELD_IDXS.append(65*4)
    FIELD_MASKS.append(0b1 << i)

with open(sys.argv[1], "rb") as fh:
    d = bson.loads(fh.read())
if not "apinfos" in d.keys():
    d["apinfos"] = []

try:
    GOOD_DUMP = d["regdumps"][0][0]
except:
    GOOD_DUMP = None

ALL_APS = []

for sublist in d["apinfos"]:
    for aplist in sublist:
        for ap in aplist:
            if not ap in ALL_APS:
                ALL_APS.append(ap)

x = np.asarray(d["delays"])
y = np.asarray(FIELD_KEYS + ALL_APS)

z_blank = np.zeros(shape=(y.shape[0], x.shape[0]))
z_not_up = np.zeros(shape=(y.shape[0], x.shape[0]))
z_dump_failed = np.zeros(shape=(y.shape[0], x.shape[0]))
z_field_modified = np.zeros(shape=(y.shape[0], x.shape[0]))

for i, delay in enumerate(d["delays"]):

    for j, field in enumerate(FIELD_KEYS):

        prob_not_up = 1 - d["up_rates"][i]
        z_not_up[j, i] = prob_not_up

        prob_dump_failed = 1 - d["dump_rates"][i] - prob_not_up
        assert prob_dump_failed >= 0
        z_dump_failed[j, i] = prob_dump_failed

        if GOOD_DUMP is not None:
            good_data_bytes = GOOD_DUMP[FIELD_IDXS[j] : FIELD_IDXS[j] + 4]
            good_data = struct.unpack("<i", good_data_bytes)[0]
            good_data &= FIELD_MASKS[j]

        n_field_modified = 0
        for dump_attempt in d["regdumps"][i]:
            field_data_bytes = dump_attempt[FIELD_IDXS[j] : FIELD_IDXS[j] + 4]
            field_data = struct.unpack("<i", field_data_bytes)[0]
            field_data &= FIELD_MASKS[j]
            if field_data != good_data:
                n_field_modified += 1

        if len(d["regdumps"][0]) != 0:
            prob_field_modified = n_field_modified / len(d["regdumps"][0])
        else:
            prob_field_modified = 0
        z_field_modified[j, i] = prob_field_modified

    for j, ap in enumerate(ALL_APS):

        n_ap_present = 0
        for aplist_attempt in d["apinfos"][i]:
            if ap in aplist_attempt:
                n_ap_present += 1

        prob_ap_present = n_ap_present / len(d["apinfos"][0])
        z_field_modified[len(FIELD_KEYS) + j, i] = prob_ap_present

plt.rcParams["axes.spines.left"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.bottom"] = False

c_not_up =          mpl.colors.LinearSegmentedColormap.from_list("", [(1, 0, 0, 0), (1, 0, 0, 1)])
c_dump_failed =     mpl.colors.LinearSegmentedColormap.from_list("", [(0, 0, 1, 0), (0, 0, 1, 1)])
c_field_modified =  mpl.colors.LinearSegmentedColormap.from_list("", [(0, 1, 0, 0), (0, 1, 0, 1)])

fig, ax = plt.subplots()
# plt.subplots_adjust(left=0.25)
ax.set_axisbelow(True)

# ax.pcolormesh(x, y, z_blank, shading="nearest", cmap=c_not_up)
ax.pcolormesh(x, y, z_not_up, shading="nearest", cmap=c_not_up)
ax.pcolormesh(x, y, z_dump_failed, shading="nearest", cmap=c_dump_failed)
ax.pcolormesh(x, y, z_field_modified, shading="nearest", cmap=c_field_modified)

ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
# ax.xaxis.set_major_locator(ticker.MultipleLocator(20))
# ax.xaxis.set_minor_locator(ticker.MultipleLocator(2))

ax.set_yticks([x+0.5 for x in ax.get_yticks()[:-1]], minor=True)
ax.grid(axis="y", which="minor", color=(0.2, 0.2, 0.2))

ax.tick_params(axis="y", length=0, colors=AXCOLOR)
ax.tick_params(axis="y", which="minor", length=0, colors=AXCOLOR)
ax.tick_params(axis="x", length=20, colors=AXCOLOR)
ax.tick_params(axis="x", which="minor", length=10, colors=AXCOLOR)

for tick in ax.get_xticklabels():
    tick.set_fontname(AXFONT)
for tick in ax.get_yticklabels():
    tick.set_fontname(AXFONT)

fig.set_facecolor(BGCOLOR)
ax.set_facecolor(BGCOLOR)

ax.invert_yaxis()
plt.show()
