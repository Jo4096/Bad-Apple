import os, sys
from PIL import Image
import struct

if len(sys.argv) < 4:
    print("How to use: python3 pack_frames.py <WIDTH> <HEIGHT> <DITHER_TYPE>")
    sys.exit(1)

W, H, FPS = map(int, sys.argv[1:4])
FRAME_BYTES = W * H // 8
frame_files = sorted([f for f in os.listdir("frames") if f.endswith(".pbm")])

def rle_compress(data: bytes) -> bytes:
    """Compressão RLE simples: (len, value)"""
    out = bytearray()
    i = 0
    while i < len(data):
        j = i + 1
        while j < len(data) and data[j] == data[i] and (j - i) < 255: 
            j += 1
        out += bytes([j - i, data[i]])
        i = j
    return out

print(f"Packing {len(frame_files)} frames ({W}x{H}) com RLE...")

out_path = "bad_apple.rle"
out_bin = open(out_path, "wb")
frames_data = []

for fi, fn in enumerate(frame_files):
    img = Image.open(os.path.join("frames", fn)).convert("1")
    data = bytearray()
    for y in range(H):
        byte, bits = 0, 0
        for x in range(W):
            pixel = 0 if img.getpixel((x, y)) > 0 else 1
            byte = (byte << 1) | pixel
            bits += 1
            if bits == 8:
                data.append(byte)
                byte, bits = 0, 0
        if bits:
            data.append(byte << (8 - bits))
            
    comp = rle_compress(data)
    out_bin.write(struct.pack("<H", len(comp)))
    out_bin.write(comp)
    frames_data.append(comp)

out_bin.close()
print(f"Saved: {out_path} ({os.path.getsize(out_path)/1024:.1f} KB)")

data_path = "bad_apple_data.h"
print(f"Generating a inline version for C++: {data_path}")
with open(data_path, "w") as h:
    h.write("// Generated automatically by pack_frames.py\n#pragma once\n")
    h.write("#include <stdint.h>\n\n")
    h.write(f"#define BAD_APPLE_WIDTH {W}\n#define BAD_APPLE_HEIGHT {H}\n")
    h.write(f"#define BAD_APPLE_FPS {FPS}\n#define BAD_APPLE_FRAME_COUNT {len(frames_data)}\n\n")
    
    offsets = [0]
    current_offset = 0
    for comp in frames_data:
        current_offset += 2 + len(comp)
        offsets.append(current_offset)
    
    h.write("static const uint32_t bad_apple_offsets[] = {\n    ")
    h.write(", ".join(str(o) for o in offsets[:-1]))
    h.write("\n};\n\n")

    h.write("static const uint8_t bad_apple_data[] = {\n")
    total_bytes = 0
    for i, comp in enumerate(frames_data):
        h.write(f"    // Frame {i} (RLE: {len(comp)} bytes)\n    ")
        size_bytes = struct.pack("<H", len(comp))
        h.write(f"0x{size_bytes[0]:02X}, 0x{size_bytes[1]:02X}, ")
        total_bytes += 2

        for j, b in enumerate(comp):
            h.write(f"0x{b:02X}, ")
            total_bytes += 1
            if (total_bytes - offsets[i]) % 16 == 0:
                h.write("\n    ")
        h.write("\n")
    h.write("};\n\n")
    h.write(f"// Total: {total_bytes} bytes (~{total_bytes/1024:.1f} KB)\n")

print(f"Generated: {data_path} (~{total_bytes/1024:.1f} KB)")
