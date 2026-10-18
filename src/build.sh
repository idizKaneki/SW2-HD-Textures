#!/bin/sh
# Builds SW2HD.asi (32-bit Windows DLL). Needs Python 3 and: pip install ziglang==0.17.0
python3 -m ziglang cc -target x86-windows-gnu -O2 -s -shared -Wall -o SW2HD.asi sw2hd.c version.rc -lkernel32 -luser32 -Wl,--subsystem,windows
