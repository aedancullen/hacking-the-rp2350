# Hacking the RP2350
This repo contains resources used in [my talk at 38C3](https://media.ccc.de/v/38c3-hacking-the-rp2350) about solving the [RP2350 Hacking Challenge](https://github.com/raspberrypi/rp2350_hacking_challenge).

---

If you're specifically interested in code,
- [`4_siri_set_a_timer/`](https://github.com/aedancullen/hacking-the-rp2350/tree/master/4_siri_set_a_timer) contains tools used for sweeping the `USB_OTP_VDD` pulse and plotting the results
- [`misc/`](https://github.com/aedancullen/hacking-the-rp2350/tree/master/misc) contains an experiment to try to find the Synopsys/Sidense "boot instruction/command" in SBPI, which wasn't successful (yet) and wasn't mentioned in the talk.

Of course, you don't need any code to perform this attack. Just drop `USB_OTP_VDD` for 50 μs or so across the `CRIT0` and `CRIT1` OTP PSM reads, which on my chips are around 220-250 μs from the characteristic current spike that marks the beginning of the OTP PSM sequence. (I trigger my scope on that spike.)

If you're trying it blind without viewing the current waveform, you should eventually get a success by bumping the pulse delay in steps of 5 μs (up to probably 50+ μs in each direction because of ROSC variability.)

If you're not using a script to automatically try connecting a debugger, you can use power consumption of the board as an indicator of success. Since the secure challenge code cannot run when the RISC-V cores are selected, the power consumption of the board on `3V3` will be closer to 10 mW than the typical 50-60 mW.

## Full-resolution die images

The following images are excluded from the [`die_strip/`](https://github.com/aedancullen/hacking-the-rp2350/tree/master/2_anti_fuse_fuse_club/die_strip) and [`die_top/`](https://github.com/aedancullen/hacking-the-rp2350/tree/master/2_anti_fuse_fuse_club/die_top) directories because they are large:
- `die_strip_03_1000x_stitch.tif` (535 MiB)
- `die_strip_04_1000x_stitch.tif` (556 MiB)
- `die_top_04_1000x_stitch.jpg` (128 MiB)
- `die_top_09_1000x_stitch.jpg` (135 MiB)

A `.zip` containing these can be downloaded [here](https://drive.google.com/uc?export=download&id=1EvxP071yHd-2c9h0VoO2_HSkNGtlrwxj).

Scaled-down versions of a few are available directly in [`2_anti_fuse_fuse_club/`](https://github.com/aedancullen/hacking-the-rp2350/tree/master/2_anti_fuse_fuse_club).

## Variation: grab the guard data at the end of the "boot instruction"

(not discussed in the talk)

Since the 16 initial reads performed by the boot instruction also use the `0x333333` guard in some way (though a second may also be used), this data is left around during some of the "dead time" between those 16 reads and the beginning of RPi's dense series of reads.

Therefore, rather than starting the power dropout at the beginning of the `CRIT0` reads and needing to contend with meaningful data every microsecond or so, we can instead start the power outage during this wide gap after the boot instruction and simply extend it for longer to cover `CRIT0`/`CRIT1`. A 200 μs pulse is suitable.

The plot below shows the result of sweeping the 200 μs pulse on my non-secure board:

![variation_1.png](/misc/variation_1.png)

(generated from [`4_siri_set_a_timer/data/chall_nsec_m33_delay0to600_width200_step0.1_apinfo.bson`](https://github.com/aedancullen/hacking-the-rp2350/tree/master/4_siri_set_a_timer/data/chall_nsec_m33_delay0to600_width200_step0.1_apinfo.bson))

The first period of RISC-V success from 180-210 μs is new, due to carrying the threes from the tail end of the boot instruction. The subsequent `CRIT0` period is still visible in the debug AP readout at 250 μs (but afterward we start covering high `KEY_VALID` bits with our long outage.)

In the first period of success, the start of our dropout does not contend with reads of real data. Why, then, are there still "stripes" of failure in this new wide period of RISC-V success?
The reason for these narrower stripes of failure is that the end of our 200 μs still falls atop normal reads. There is some analog weirdness where data is corrupted very briefly to `0xffffff` as `USB_OTP_VDD` rises, even if you were holding the latched threes as usual while it was off.

Also note that the threes are available for **some** of the "dead time". Clearly, something else happens at ~210 μs for the second half of the dead time before RPi's dense series of reads begins with `CRIT0`. There are three corresponding blips visible in the current waveform. Mysteries...

---

All images under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
