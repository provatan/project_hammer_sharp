
from PIL import Image
import struct


# ---------------------------------------------
# IMAGE FORMAT
# ---------------------------------------------

FORMATS = {
    0: ("RGBA", 4),
    2: ("RGB", 3),
    3: ("BGR", 3),
    12: ("BGRA", 4),
}


def image_size(width, height, fmt, depth=1):
    depth = max(1, depth)

    if fmt in FORMATS:
        return width * height * FORMATS[fmt][1] * depth

    if fmt == 13 or fmt == 20:
        return ((width + 3) // 4) * ((height + 3) // 4) * 8 * depth

    if fmt in (14, 15):
        return ((width + 3) // 4) * ((height + 3) // 4) * 16 * depth

    raise ValueError(f"Неподдерживаемый формат пикселей: {fmt}")


# ---------------------------------------------
# RGB565
# ---------------------------------------------

def rgb565(value):

    r = (value >> 11) & 31
    g = (value >> 5) & 63
    b = value & 31

    return (
        (r * 255 + 15) // 31,
        (g * 255 + 31) // 63,
        (b * 255 + 15) // 31
    )


# ---------------------------------------------
# DXT COLOR BLOCK
# ---------------------------------------------

def color_block(data, allow_transparency=True):

    c0, c1, indices = struct.unpack("<HHI", data)

    color0 = rgb565(c0)
    color1 = rgb565(c1)

    if c0 > c1 or not allow_transparency:
        colors = [
            color0,
            color1,
            tuple((2 * a + b) // 3 for a, b in zip(color0, color1)),
            tuple((a + 2 * b) // 3 for a, b in zip(color0, color1))
        ]

    else:
        colors = [
            color0,
            color1,
            tuple((a + b) // 2 for a, b in zip(color0, color1)),
            (0, 0, 0)
        ]

    result = []

    for i in range(16):

        index = (indices >> (2 * i)) & 3

        color = colors[index]

        alpha = 0 if index == 3 and c0 <= c1 and allow_transparency else 255

        result.append((*color, alpha))

    return result


# ---------------------------------------------
# DXT ALPHA BLOCK
# ---------------------------------------------

def alpha_block(data):

    a0 = data[0]
    a1 = data[1]

    bits = int.from_bytes(data[2:8], "little")

    values = [a0, a1]

    if a0 > a1:

        for i in range(1, 7):
            values.append(
                ((7 - i) * a0 + i * a1) // 7
            )

    else:

        for i in range(1, 5):
            values.append(
                ((5 - i) * a0 + i * a1) // 5
            )

        values.extend([0, 255])

    return [
        values[(bits >> (3 * i)) & 7]
        for i in range(16)
    ]


# ---------------------------------------------
# DXT DECODER
# ---------------------------------------------

def decode_dxt(data, width, height, fmt):

    block_size = 8 if fmt in (13, 20) else 16

    image = Image.new("RGBA", (width, height))

    blocks_x = (width + 3) // 4
    blocks_y = (height + 3) // 4

    expected = blocks_x * blocks_y * block_size

    if len(data) < expected:
        raise ValueError("Недостаточно данных DXT.")

    offset = 0

    for by in range(blocks_y):
        for bx in range(blocks_x):

            if fmt in (13, 20):

                colors = color_block(
                    data[offset:offset + 8],
                    allow_transparency=(fmt == 13)
                )

                offset += 8

                if fmt == 20:
                    for i in range(16):
                        colors[i] = (*colors[i][:3], 255)

            elif fmt == 14:

                alpha_data = data[offset:offset + 8]
                color_data = data[offset + 8:offset + 16]

                alphas = [
                    (alpha_data[i // 2] >> ((i % 2) * 4)) & 15
                    for i in range(16)
                ]

                colors = color_block(color_data, False)

                colors = [
                    (*colors[i][:3], alphas[i] * 17)
                    for i in range(16)
                ]

                offset += 16

            else:

                alphas = alpha_block(data[offset:offset + 8])

                colors = color_block(
                    data[offset + 8:offset + 16],
                    False
                )

                colors = [
                    (*colors[i][:3], alphas[i])
                    for i in range(16)
                ]

                offset += 16

            for y in range(4):
                for x in range(4):

                    px = bx * 4 + x
                    py = by * 4 + y

                    if px >= width or py >= height:
                        continue

                    color = colors[y * 4 + x]

                    image.putpixel((px, py), color)

    return image


# ---------------------------------------------
# MAIN DECODER
# ---------------------------------------------

def decode_image(data, width, height, fmt):

    if fmt in (13, 14, 15, 20):
        return decode_dxt(data, width, height, fmt)

    if fmt not in FORMATS:
        raise ValueError(f"Формат {fmt} не поддерживается.")

    mode, _ = FORMATS[fmt]

    if fmt == 3:
        return Image.frombytes(
            "RGB", (width, height), data, "raw", "BGR"
        )

    if fmt == 12:
        return Image.frombytes(
            "RGBA", (width, height), data, "raw", "BGRA"
        )

    return Image.frombytes(mode, (width, height), data).convert("RGBA")
