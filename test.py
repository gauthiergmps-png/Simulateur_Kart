from pathlib import Path

import numpy 
import struct

LG2010_XRK = Path(__file__).resolve().parent / "C_et_T" / "C_et_T_files" / "xrk_files" / "LG2010.xrk"
with open(LG2010_XRK, "rb") as f:
    chunk = f.read(32)

print(struct.unpack("8f", chunk))  # test floats