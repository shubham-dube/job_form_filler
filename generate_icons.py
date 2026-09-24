import zlib
import struct
from pathlib import Path

def create_png(width, height, color_fn):
    # PNG signature
    png = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
    png += struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
    
    # Raw pixel data (RGBA) with filter byte 0 at start of each scanline
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # Filter byte None
        for x in range(width):
            r, g, b, a = color_fn(x, y, width, height)
            raw.extend([r, g, b, a])
            
    # IDAT chunk
    compressed = zlib.compress(bytes(raw), 9)
    idat_crc = zlib.crc32(b'IDAT' + compressed)
    png += struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)
    
    # IEND chunk
    iend_crc = zlib.crc32(b'IEND')
    png += struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
    
    return png

def form_filler_icon(x, y, w, h):
    # Normalize coordinates to 0..1
    nx = x / w
    ny = y / h
    
    # Rounded rectangle mask with border radius 0.2
    cx = abs(nx - 0.5)
    cy = abs(ny - 0.5)
    
    # Distance from center
    dist = ((nx - 0.5)**2 + (ny - 0.5)**2)**0.5
    
    # Background gradient: Indigo (#6366f1) to Purple (#8b5cf6)
    bg_r = int(99 + (139 - 99) * (nx + ny) / 2)
    bg_g = int(102 + (92 - 102) * (nx + ny) / 2)
    bg_b = int(241 + (246 - 241) * (nx + ny) / 2)
    
    # Lightning / Sparkle / Form check symbol in center
    # In center (0.35 to 0.65): draw bright white/cyan diamond/sparkle
    is_center = False
    dx = abs(nx - 0.5)
    dy = abs(ny - 0.5)
    if dx + dy < 0.28:
        is_center = True
        
    # Check if inside rounded icon box
    if max(cx, cy) > 0.46:
        return 0, 0, 0, 0  # Transparent outside
    
    # Rounded corners
    corner_d = ((max(0, cx - 0.36))**2 + (max(0, cy - 0.36))**2)**0.5
    if corner_d > 0.1:
        return 0, 0, 0, 0
        
    if is_center:
        # Bright cyan / white sparkle
        return 255, 255, 255, 255
    else:
        return bg_r, bg_g, bg_b, 255

icons_dir = Path("extension/icons")
icons_dir.mkdir(parents=True, exist_ok=True)

for size in (16, 48, 128):
    data = create_png(size, size, form_filler_icon)
    (icons_dir / f"icon{size}.png").write_bytes(data)
    print(f"Generated icon{size}.png ({len(data)} bytes)")
