# Copyright (c) 2024 Aedan Cullen
# portions Copyright (c) 2023 Raspberry Pi (Trading) Ltd.
# SPDX-License-Identifier: GPL-3.0-or-later

# ======= BRIDGE REGS =======

# these are RPi-side, not 3PIP-side!
# "Serial and Byte-Parallel Interface"

OTP_HW_SBPI_INSTR = 0x40120100
OTP_HW_SBPI_STATUS = 0x40120124
OTP_HW_USR = 0x40120128

OTP_SBPI_INSTR_EXEC_LSB = 30
OTP_SBPI_INSTR_IS_WR_LSB = 29
OTP_SBPI_INSTR_HAS_PAYLOAD_LSB = 28
OTP_SBPI_INSTR_PAYLOAD_SIZE_M1_LSB = 24
OTP_SBPI_INSTR_TARGET_LSB = 16
OTP_SBPI_INSTR_CMD_LSB = 8
OTP_SBPI_INSTR_SHORT_WDATA_LSB = 0

OTP_SBPI_STATUS_MISO_BITS = 0x00ff0000
OTP_SBPI_STATUS_FLAG_BITS = 0x00001000
OTP_SBPI_STATUS_INSTR_MISS_BITS = 0x00000100
OTP_SBPI_STATUS_INSTR_DONE_BITS = 0x00000010
OTP_SBPI_STATUS_RDATA_VLD_BITS = 0x00000001

# ===========================





OTP_TARGET_DAP =      0x02
OTP_TARGET_PMC =      0x3a

OTP_REG_READ =        0x80 # 10nn_nnnn: read register n
OTP_REG_WRITE =       0xc0 # 11nn_nnnn:

# vvvvvvvvvv added vvvvvvvvvv

# The above REG_READ and REG_WRITE are valid commands for both DAP and PMC.
# nn_nnnn is the address (see regs listed below for each of DAP/PMC).

# Additional commands *in this same format* used for PMC fuse programming only:
OTP_PMC_START = 0x01 # start programming
OTP_PMC_STOP = 0x02 # finish programming

# Command MSB is clearly "is register operation"

# ^^^^^^^^^^^^^^^^^^^^^^^^^^^

OTP_DAP_DR0 =         0x00 # Data 7:0
OTP_DAP_DR1 =         0x01 # Data 15:8
OTP_DAP_ECC =         0x20 # Data 23:16
OTP_DAP_RQ0_RFMR =    0x30 # Read Mode Control, Charge Pump Control
OTP_DAP_RQ1_VRMR =    0x31 # Read Voltage Control (VRR), CP enable
OTP_DAP_RQ2_OVLR =    0x32 # IPS VQQ and VPP Control
OTP_DAP_RQ3_IPCR =    0x33 # VDD detect, Ext. Ref. enable, IPS enable, OSC. Output Mode, Ext Ck enable, Ref Bias Disable
OTP_DAP_RQ4_OSCR =    0x34 # Reserved for Test
OTP_DAP_RQ5_ORCR =    0x35 # OTP ROM control, Test Mode Controls
OTP_DAP_RQ6_ODCR =    0x36 # Read Timer Control
OTP_DAP_RQ7_IPCR2 =   0x37 # IPS CP sync. Input Control, IPS reserved Control
OTP_DAP_RQ8_OCER =    0x38 # OTP Bank Selection, PD control
OTP_DAP_RQ9_RES0 =    0x39 # Reserved
OTP_DAP_RQ10_DPCR =   0x3a # DATAPATH Control: (msb - lsb) {MUXQ[1:0], PASS, brpGEN. brpDIS, eccTST, eccGEN, eccDIS}
OTP_DAP_RQ11_DPCR_2 = 0x3b # DATAPATH Control 2 – multi-bit prog. control {5’b00000, MBPC[2:0]}
OTP_DAP_CQ0 =         0x3c # OTP address LSBs
OTP_DAP_CQ1 =         0x3d # OTP address MSBs

OTP_PMC_MODE_0 =      0x30 # Bytes: 2 ; Default Read Conditions 0
OTP_PMC_MODE_1 =      0x32 # Bytes: 2 ; Read Conditions 1
OTP_PMC_MODE_2 =      0x34 # Bytes: 2 ; Read Conditions 2
OTP_PMC_MODE_3 =      0x36 # Bytes: 2 ; Specific Function Usage
OTP_PMC_TIMING_0 =    0x38 # Bytes: 1 ; Timing Control 0
OTP_PMC_TIMING_1 =    0x39 # Bytes: 1 ; Timing Control 1
OTP_PMC_TIMING_2 =    0x3a # Bytes: 1 ; Timing Control 2
OTP_PMC_DAP_ADDR =    0x3b # Bytes: 1 ; DAP ID Address
OTP_PMC_CQ =          0x3c # Bytes: 2 ; Function Control
OTP_PMC_DFSR =        0x3e # Bytes: 1 ; Flag Selection (Read Only)
OTP_PMC_CTRL_STATUS = 0x3f # Bytes: 1 ; Control Register (Write Only), STATUS (Read Only)

# vvvvvvvvvv added vvvvvvvvvv

#
# Bits in OTP_PMC_CTRL_STATUS
# 
# 0 0 0 0 _ 0 0 0 0
# | \_\_\___\_\_\_\__ programming enable/config (prior to OTP_PMC_START)
# |
# STATUS/BUSY (use w/ OTP_PMC_START and OTP_PMC_STOP commands)
#

OTP_PMC_CSR_STATUS_BITS = 0x80

# ^^^^^^^^^^^^^^^^^^^^^^^^^^^





import shlex
import argparse
import socket
import struct
import subprocess
import time
import pickle

class SBPIFuzzCommand(gdb.Command):
    """Try all possible SBPI commands."""

    def __init__(self):
        super(SBPIFuzzCommand, self).__init__("sbpi_fuzz", gdb.COMMAND_USER)

        self.parser = argparse.ArgumentParser()

    def complete(self, text, word):
        return gdb.COMPLETE_SYMBOL

    def sbpi_execute_command(self, is_wr, has_payload, payload_size_m1, target, cmd, short_wdata, execbit):
        i = gdb.inferiors()[0]

        i.write_memory(OTP_HW_USR, b"\x00\x00\x00\x00")

        sbpi_instr = (
            (is_wr << OTP_SBPI_INSTR_IS_WR_LSB) |
            (has_payload << OTP_SBPI_INSTR_HAS_PAYLOAD_LSB) |
            (payload_size_m1 << OTP_SBPI_INSTR_PAYLOAD_SIZE_M1_LSB) |
            (target << OTP_SBPI_INSTR_TARGET_LSB) |
            (cmd << OTP_SBPI_INSTR_CMD_LSB) |
            (short_wdata << OTP_SBPI_INSTR_SHORT_WDATA_LSB) |
            (execbit << OTP_SBPI_INSTR_EXEC_LSB)
        )

        i.write_memory(OTP_HW_SBPI_INSTR, struct.pack("<I", sbpi_instr))
        print("SBPI_INSTR:", i.read_memory(OTP_HW_SBPI_INSTR, 4).tobytes()[::-1].hex())

        status_mask = OTP_SBPI_STATUS_INSTR_MISS_BITS | OTP_SBPI_STATUS_INSTR_DONE_BITS

        print("Waitng for bridge...")
        status_val = struct.unpack("<I", i.read_memory(OTP_HW_SBPI_STATUS, 4).tobytes())[0]
        while (status_val & status_mask) == 0:
            time.sleep(0.001)
            status_val = struct.unpack("<I", i.read_memory(OTP_HW_SBPI_STATUS, 4).tobytes())[0]

        print("MISO:", hex((status_val & OTP_SBPI_STATUS_MISO_BITS) >> 16))
        print("FLAG:", (status_val & OTP_SBPI_STATUS_FLAG_BITS) != 0)
        print("INSTR_MISS:", (status_val & OTP_SBPI_STATUS_INSTR_MISS_BITS) != 0)
        print("INSTR_DONE:", (status_val & OTP_SBPI_STATUS_INSTR_DONE_BITS) != 0)
        print("RDATA_VLD:", (status_val & OTP_SBPI_STATUS_RDATA_VLD_BITS) != 0)

        # write-clear
        i.write_memory(OTP_HW_SBPI_STATUS, b"\xff\xff\xff\xff")
        status_val = struct.unpack("<I", i.read_memory(OTP_HW_SBPI_STATUS, 4).tobytes())[0]
        assert (status_val & status_mask) == 0

    def invoke(self, args, from_tty):
        try:
            args = self.parser.parse_args(shlex.split(args))
        except SystemExit:
            return

        target = OTP_TARGET_DAP
        for cmd in range(0x00, 128): # don't hit reg read/write (MSB) for now.
            print("TARGET:", hex(target), "\ttrying CMD:", hex(cmd), "\t <enter>")
            input()
            self.sbpi_execute_command(1, 0, 0, target, cmd, 0, 1)
            print()

        target = OTP_TARGET_PMC
        for cmd in range(0x00, 128): # don't hit reg read/write (MSB) for now.
            print("TARGET:", hex(target), "\ttrying CMD:", hex(cmd), "\t <enter>")
            input()
            self.sbpi_execute_command(1, 0, 0, target, cmd, 0, 1)
            print()

SBPIFuzzCommand()
