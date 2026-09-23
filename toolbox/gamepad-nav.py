#!/usr/bin/env python3
"""
UMU Runner Toolbox - gamepad navigation helper.
Reads Linux evdev gamepad events and emits keyboard arrows/Enter/Esc through uinput.
No third-party Python modules required.
"""

import os
import sys
import glob
import time
import struct
import fcntl
import select
import signal

# input-event constants
EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03
SYN_REPORT = 0

BTN_SOUTH = 304   # A / Cross
BTN_EAST  = 305   # B / Circle
BTN_START = 315
BTN_DPAD_UP = 544
BTN_DPAD_DOWN = 545
BTN_DPAD_LEFT = 546
BTN_DPAD_RIGHT = 547

ABS_X = 0
ABS_Y = 1
ABS_HAT0X = 16
ABS_HAT0Y = 17

KEY_ESC = 1
KEY_ENTER = 28
KEY_UP = 103
KEY_LEFT = 105
KEY_RIGHT = 106
KEY_DOWN = 108

BUS_USB = 0x03

# Linux ioctl helpers
_IOC_NRBITS=8; _IOC_TYPEBITS=8; _IOC_SIZEBITS=14; _IOC_DIRBITS=2
_IOC_NRSHIFT=0
_IOC_TYPESHIFT=_IOC_NRSHIFT+_IOC_NRBITS
_IOC_SIZESHIFT=_IOC_TYPESHIFT+_IOC_TYPEBITS
_IOC_DIRSHIFT=_IOC_SIZESHIFT+_IOC_SIZEBITS
_IOC_NONE=0
_IOC_WRITE=1
_IOC_READ=2
def _IOC(direction, t, nr, size):
    return (direction << _IOC_DIRSHIFT) | (ord(t) << _IOC_TYPESHIFT) | (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT)
def _IOW(t,nr,size): return _IOC(_IOC_WRITE,t,nr,size)
def _IOR(t,nr,size): return _IOC(_IOC_READ,t,nr,size)

UI_SET_EVBIT = _IOW('U', 100, 4)
UI_SET_KEYBIT = _IOW('U', 101, 4)
UI_DEV_CREATE = _IOW('U', 1, 0)
UI_DEV_DESTROY = _IOW('U', 2, 0)

EVIOCGNAME_LEN = 256
EVIOCGNAME = _IOC(_IOC_READ, 'E', 0x06, EVIOCGNAME_LEN)
EVIOCGBIT_KEY = lambda n: _IOC(_IOC_READ, 'E', 0x20 + EV_KEY, n)

EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

running = True
def stop(*_):
    global running
    running = False
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

def dev_name(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        buf = bytearray(EVIOCGNAME_LEN)
        fcntl.ioctl(fd, EVIOCGNAME, buf, True)
        os.close(fd)
        return bytes(buf).split(b"\0",1)[0].decode(errors="replace")
    except Exception:
        return ""

def has_gamepad_button(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        # 768 key bits = 96 bytes is enough for BTN_* range.
        bits = bytearray(96)
        fcntl.ioctl(fd, EVIOCGBIT_KEY(len(bits)), bits, True)
        os.close(fd)
        for code in (BTN_SOUTH, BTN_EAST, BTN_START):
            if bits[code // 8] & (1 << (code % 8)):
                return True
    except Exception:
        pass
    return False

def find_gamepads():
    candidates = []
    for p in sorted(glob.glob("/dev/input/event*")):
        if not has_gamepad_button(p):
            continue
        n = dev_name(p)
        low = n.lower()
        # Exclude obvious keyboard/mouse pseudo-devices.
        if "keyboard" in low or "mouse" in low or "touchpad" in low:
            continue
        candidates.append((p,n))
    return candidates

def make_uinput_keyboard():
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
    fcntl.ioctl(fd, UI_SET_EVBIT, EV_SYN)
    for key in (KEY_ESC, KEY_ENTER, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT):
        fcntl.ioctl(fd, UI_SET_KEYBIT, key)

    # struct uinput_user_dev:
    # name[80], input_id (HHHH), ff_effects_max (I),
    # absmax/min/fuzz/flat arrays (4 * 64 ints)
    name = b"UMU-Toolbox-PadKeys"
    data = bytearray(1116)
    data[:len(name)] = name
    struct.pack_into("HHHH", data, 80, BUS_USB, 0x1209, 0x0001, 1)
    os.write(fd, data)
    fcntl.ioctl(fd, UI_DEV_CREATE)
    time.sleep(0.25)
    return fd

def emit(fd, key):
    now = time.time()
    sec = int(now); usec = int((now-sec)*1_000_000)
    os.write(fd, struct.pack(EVENT_FMT, sec,usec,EV_KEY,key,1))
    os.write(fd, struct.pack(EVENT_FMT, sec,usec,EV_SYN,SYN_REPORT,0))
    time.sleep(0.015)
    now = time.time()
    sec = int(now); usec = int((now-sec)*1_000_000)
    os.write(fd, struct.pack(EVENT_FMT, sec,usec,EV_KEY,key,0))
    os.write(fd, struct.pack(EVENT_FMT, sec,usec,EV_SYN,SYN_REPORT,0))

def main():
    pads = find_gamepads()
    if not pads:
        return 0

    try:
        ufd = make_uinput_keyboard()
    except Exception as e:
        print(f"[gamepad-nav] uinput unavailable: {e}", file=sys.stderr)
        return 0

    fds = {}
    try:
        for p,n in pads:
            try:
                fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
                fds[fd] = {"path":p, "name":n, "x":0, "y":0, "hatx":0, "haty":0}
            except OSError:
                pass

        last = {}
        def gated(key):
            t=time.monotonic()
            if t-last.get(key,0) >= 0.16:
                emit(ufd,key); last[key]=t

        while running and fds:
            ready,_,_ = select.select(list(fds), [], [], 0.25)
            for fd in ready:
                try:
                    raw = os.read(fd, EVENT_SIZE * 32)
                except OSError:
                    continue
                for off in range(0, len(raw)-EVENT_SIZE+1, EVENT_SIZE):
                    _,_,etype,code,value = struct.unpack_from(EVENT_FMT, raw, off)
                    if etype == EV_KEY and value == 1:
                        if code == BTN_SOUTH or code == BTN_START:
                            gated(KEY_ENTER)
                        elif code == BTN_EAST:
                            gated(KEY_ESC)
                        elif code == BTN_DPAD_UP:
                            gated(KEY_UP)
                        elif code == BTN_DPAD_DOWN:
                            gated(KEY_DOWN)
                        elif code == BTN_DPAD_LEFT:
                            gated(KEY_LEFT)
                        elif code == BTN_DPAD_RIGHT:
                            gated(KEY_RIGHT)
                    elif etype == EV_ABS:
                        # D-pad hats are preferred.
                        if code == ABS_HAT0X:
                            if value < 0: gated(KEY_LEFT)
                            elif value > 0: gated(KEY_RIGHT)
                        elif code == ABS_HAT0Y:
                            if value < 0: gated(KEY_UP)
                            elif value > 0: gated(KEY_DOWN)
                        # Also allow left stick; common signed ranges are approx +/-32767.
                        elif code == ABS_X:
                            if value < -16000: gated(KEY_LEFT)
                            elif value > 16000: gated(KEY_RIGHT)
                        elif code == ABS_Y:
                            if value < -16000: gated(KEY_UP)
                            elif value > 16000: gated(KEY_DOWN)
    finally:
        for fd in list(fds):
            try: os.close(fd)
            except OSError: pass
        try:
            fcntl.ioctl(ufd, UI_DEV_DESTROY)
            os.close(ufd)
        except Exception:
            pass
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
