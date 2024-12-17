# Copyright (c) 2024 Aedan Cullen
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import pickle
import struct
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

FIELD_KEYS = []
FIELD_IDXS = []
FIELD_MASKS = []

for i in range(64):
    FIELD_KEYS.append(f"0x{i*4:03x}:    SW_LOCK{i}")
    FIELD_IDXS.append(i*4)
    FIELD_MASKS.append(0xffffffff)

for i in range(8):
    FIELD_KEYS.append(f"0x148:    CRITICAL[{i}]")
    FIELD_IDXS.append(64*4)
    FIELD_MASKS.append(0b1 << i)

for i in range(8):
    FIELD_KEYS.append(f"0x14c:    KEY_VALID[{i}]")
    FIELD_IDXS.append(65*4)
    FIELD_MASKS.append(0b1 << i)

with open(sys.argv[1], "rb") as fh:
    delays, widths, up_rates, dump_rates, regdumps = pickle.load(fh)

GOOD_DUMP = regdumps[0][0] # ewww, assuming first is perfect

x = np.asarray(delays)
y = np.asarray(FIELD_KEYS)

z_not_up = np.zeros(shape=(y.shape[0], x.shape[0]))
z_dump_failed = np.zeros(shape=(y.shape[0], x.shape[0]))
z_field_modified = np.zeros(shape=(y.shape[0], x.shape[0]))

for i, delay in enumerate(delays):
    for j, field in enumerate(FIELD_KEYS):

        prob_not_up = 1 - up_rates[i]
        z_not_up[j, i] = prob_not_up

        prob_dump_failed = 1 - dump_rates[i] - prob_not_up
        assert prob_dump_failed >= 0
        z_dump_failed[j, i] = prob_dump_failed

        good_data_bytes = GOOD_DUMP[FIELD_IDXS[j] : FIELD_IDXS[j] + 4]
        good_data = struct.unpack("<i", good_data_bytes)[0]
        good_data &= FIELD_MASKS[j]

        n_field_modified = 0
        for dump_attempt in regdumps[i]:
            field_data_bytes = dump_attempt[FIELD_IDXS[j] : FIELD_IDXS[j] + 4]
            field_data = struct.unpack("<i", field_data_bytes)[0]
            field_data &= FIELD_MASKS[j]
            if field_data != good_data:
                n_field_modified += 1

        prob_field_modified = n_field_modified / len(regdumps[0]) # ewww, assuming first is perfect
        z_field_modified[j, i] = prob_field_modified

plt.rcParams["axes.spines.left"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.bottom"] = False

plt.style.use("dark_background")

cm1 = mpl.colors.LinearSegmentedColormap.from_list("", [(1, 0, 0, 0), (1, 0, 0, 1)])
cm2 = mpl.colors.LinearSegmentedColormap.from_list("", [(0, 1, 0, 0), (0, 1, 0, 1)])
cm3 = mpl.colors.LinearSegmentedColormap.from_list("", [(0, 0, 1, 0), (0, 0, 1, 1)])

fig, ax = plt.subplots()
ax.set_axisbelow(True)

ax.pcolormesh(x, y, z_not_up, shading="nearest", cmap=cm1)
ax.pcolormesh(x, y, z_dump_failed, shading="nearest", cmap=cm2)
ax.pcolormesh(x, y, z_field_modified, shading="nearest", cmap=cm3)

ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))

ax.set_yticks([x+0.5 for x in ax.get_yticks()[:-1]], minor=True)
ax.grid(axis="y", which="minor", color=(0.2, 0.2, 0.2))

ax.tick_params(axis="y", length=0)
ax.tick_params(axis="y", which="minor", length=0)
ax.tick_params(axis="x", length=10)
ax.tick_params(axis="x", which="minor", length=5)

plt.gca().invert_yaxis()
plt.show()
