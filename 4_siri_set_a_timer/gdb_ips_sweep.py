# Copyright (c) 2024 Aedan Cullen
# SPDX-License-Identifier: GPL-3.0-or-later

M33_GDB_SERVER = """JLinkGDBServer -device CORTEX-M33 -if SWD"""
M33_GDB_TARGET = """target remote :2331"""

RV_GDB_SERVER = """../src/openocd -f interface/jlink.cfg -c "adapter speed 5000" -c "set USE_CORE 0" -f target/rp2350-riscv.cfg"""
RV_GDB_TARGET = """target remote :3333"""

COMMANDER = """JLinkExe -device CORTEX-M33 -if SWD -speed 4000"""

import shlex
import argparse
import socket
import struct
import subprocess
import time
import bson

class IPSSweepCommand(gdb.Command):
    """Perform a 2D sweep of IPS-drop delays and widths."""

    def __init__(self):
        super(IPSSweepCommand, self).__init__("ips_sweep", gdb.COMMAND_USER)

        self.parser = argparse.ArgumentParser()

        self.parser.add_argument("outfile", help="output file", type=str)

        self.parser.add_argument("-minD", help="smallest drop delay (us)", type=float, default=0)
        self.parser.add_argument("-maxD", help="largest drop delay (us)", type=float, default=600)
        self.parser.add_argument("-minW", help="smallest drop width (us)", type=float, default=50)
        self.parser.add_argument("-maxW", help="largest drop width (us)", type=float, default=50)

        self.parser.add_argument("-stepD", help="drop delay increment size (us)", type=float, default=1)
        self.parser.add_argument("-stepW", help="drop width increment size (us)", type=float, default=1)

        self.parser.add_argument("-n", help="number of tries", type=int, default=10)

        self.parser.add_argument("--rv", help="expect RISC-V to come up, not M33", action="store_true")
        self.parser.add_argument("--verbose", help="show full output of GDB server", action="store_true")
        self.parser.add_argument("--apinfo", help="also collect debug AP addresses", action="store_true")

    def complete(self, text, word):
        return gdb.COMPLETE_SYMBOL

    def waveforms_send_attempt(self, sock, delay, width):
        payload = struct.pack("25s25s", f"{delay}us".encode(), f"{width}us".encode())
        sock.send(payload)
        time.sleep(0.1)

    def gdbserver_try_connect(self, rv=False, verbose=False):
        cmd = M33_GDB_SERVER if not rv else RV_GDB_SERVER
        if verbose:
            proc = subprocess.Popen(cmd, shell=True,
                                    stdin=subprocess.PIPE)
        else:
            proc = subprocess.Popen(cmd, shell=True,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            return proc
        return None

    def dump_regs(self):
        i = gdb.inferiors()[0]
        sw_lock_regs = i.read_memory(0x40120000, 64*4).tobytes()
        critical_reg = i.read_memory(0x40120000 + 0x148, 1*4).tobytes()
        key_valid_reg = i.read_memory(0x40120000 + 0x14c, 1*4).tobytes()
        return sw_lock_regs + critical_reg + key_valid_reg

    def get_apinfo(self):
        proc = subprocess.Popen(COMMANDER, shell=True,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        proc.stdin.write(b"connect\n")
        proc.stdin.flush()

        lastlines = []
        line = proc.stdout.readline()
        while not b"Iterating through AP map" in line:
            if b"Error" in line:
                break
            lastlines.append(line)
            if len(lastlines) > 2:
                lastlines.pop(0)
            line = proc.stdout.readline()

        proc.terminate()
        proc.wait()

        aps = []
        for lastline in lastlines:
            if b"APAddr" in lastline:
                aps.append(lastline)
        return aps

    def invoke(self, args, from_tty):
        try:
            args = self.parser.parse_args(shlex.split(args))
        except SystemExit:
            return

        sock = socket.socket()
        sock.connect(("127.0.0.1", 50000))

        delays = []
        widths = []
        up_rates = []
        dump_rates = []
        regdumps = []
        apinfos = []

        delay = args.minD
        while delay <= args.maxD:
            width = args.minW
            while width <= args.maxW:

                up_success = 0
                dump_success = 0
                regdump = []
                apinfo = []
                for i in range(args.n):

                    self.waveforms_send_attempt(sock, delay, width)
                    server = self.gdbserver_try_connect(rv=args.rv, verbose=args.verbose)

                    if server is not None:
                        try:
                            gdb.execute(M33_GDB_TARGET if not args.rv else RV_GDB_TARGET)
                            up_success += 1
                        except gdb.error:
                            server.terminate()
                            server.wait()
                            print(f"{delay} {width} #{i+1} not up")
                            continue
                        try:
                            regdump.append(self.dump_regs())
                            dump_success += 1
                            print(f"{delay} {width} #{i+1} OK")
                        except gdb.MemoryError:
                            print(f"{delay} {width} #{i+1} dump failed")
                        gdb.execute("disconnect")
                        server.terminate()
                        server.wait()
                    else:
                        print(f"{delay} {width} #{i+1} not up")

                    if args.apinfo:
                        apinfo.append(self.get_apinfo())

                delays.append(delay)
                widths.append(width)
                up_rates.append(up_success/args.n)
                dump_rates.append(dump_success/args.n)
                regdumps.append(regdump)
                apinfos.append(apinfo)

                width += args.stepW
            delay += args.stepD

        out = {"delays": delays, "widths": widths, "up_rates": up_rates, "dump_rates": dump_rates, "regdumps": regdumps}
        if args.apinfo:
            out["apinfos"] = apinfos
        with open(args.outfile, "wb") as fh:
            fh.write(bson.dumps(out))

IPSSweepCommand()
