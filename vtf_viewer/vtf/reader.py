
import struct
import os

from .decoder import decode_image, image_size


class VTFReader:

    def __init__(self, filepath):

        self.filepath = filepath
        self.info = {}

    # ---------------------------------------------
    # READ
    # ---------------------------------------------

    def read(self):

        with open(self.filepath, "rb") as file:

            signature = file.read(4)

            if signature != b"VTF\x00":
                raise ValueError("Неверная сигнатура VTF.")

            major, minor, header_size = struct.unpack(
                "<III", file.read(12)
            )

            if major != 7 or minor > 5:
                raise ValueError(
                    f"Неподдерживаемая версия VTF {major}.{minor}"
                )

            if minor > 2:
                return self.read_modern(file, minor, header_size)

            return self.read_legacy(file, minor, header_size)

    # ---------------------------------------------
    # COMMON HEADER
    # ---------------------------------------------


    def read_common(self, file, minor, header_size):

        file.seek(16)

        width, height = struct.unpack("<HH", file.read(4))
        flags = struct.unpack("<I", file.read(4))[0]

        frames, first_frame = struct.unpack("<HH", file.read(4))

        file.seek(52)

        high_format = struct.unpack("<i", file.read(4))[0]
        mipmaps = file.read(1)[0]

        low_format = struct.unpack("<i", file.read(4))[0]

        low_width = file.read(1)[0]
        low_height = file.read(1)[0]

        depth = 1

        if minor >= 2:
            depth = struct.unpack("<H", file.read(2))[0]

        return {
            "major": 7,
            "minor": minor,
            "header_size": header_size,
            "width": width,
            "height": height,
            "flags": flags,
            "frames": max(1, frames),
            "first_frame": first_frame,
            "format": high_format,
            "mipmaps": mipmaps,
            "low_format": low_format,
            "low_width": low_width,
            "low_height": low_height,
            "depth": max(1, depth)
        }


    # ---------------------------------------------
    # LEGACY 7.0 - 7.2
    # ---------------------------------------------

    def read_legacy(self, file, minor, header_size):

        info = self.read_common(file, minor, header_size)

        low_size = 0

        if info["low_width"] and info["low_height"]:
            low_size = image_size(
                info["low_width"],
                info["low_height"],
                info["low_format"]
            )

        image_offset = header_size + low_size

        info["image_offset"] = image_offset

        return self.read_pixels(
            file,
            info,
            image_offset
        )

    # ---------------------------------------------
    # MODERN 7.3 - 7.5
    # ---------------------------------------------

    def read_modern(self, file, minor, header_size):

        info = self.read_common(file, minor, header_size)

        file.seek(68)

        num_resources = struct.unpack("<I", file.read(4))[0]

        if num_resources > 32:
            raise ValueError("Некорректное количество ресурсов.")

        resources = {}

        file.seek(80)

        for _ in range(num_resources):

            entry = file.read(8)

            if len(entry) != 8:
                raise ValueError("Повреждённая таблица ресурсов.")

            resource_type = entry[:3]
            resource_flags = entry[3]
            resource_data = struct.unpack("<I", entry[4:])[0]

            resources[resource_type] = {
                "flags": resource_flags,
                "data": resource_data
            }

        # High resolution image resource

        image_resource = resources.get(b"\x30\x00\x00")

        if image_resource is None:
            raise ValueError("Не найден ресурс High Resolution Image.")

        if image_resource["flags"] & 0x02:
            raise ValueError("Ресурс изображения не содержит данных.")

        image_offset = image_resource["data"]

        info["resources"] = resources
        info["resource_count"] = num_resources
        info["image_offset"] = image_offset

        return self.read_pixels(
            file,
            info,
            image_offset
        )

    # ---------------------------------------------
    # PIXELS
    # ---------------------------------------------

    def read_pixels(self, file, info, image_offset):

        width = info["width"]
        height = info["height"]

        fmt = info["format"]
        mipmaps = info["mipmaps"]

        frames = info["frames"]
        depth = info["depth"]

        # Environment map: six faces.
        # The seventh legacy sphere-map face is not selected here.

        faces = 6 if info["flags"] & 0x4000 else 1

        # Image data is stored from the smallest mip to the largest.

        offset = image_offset

        for level in range(mipmaps - 1, 0, -1):

            mip_width = max(1, width >> level)
            mip_height = max(1, height >> level)
            mip_depth = max(1, depth >> level)

            offset += (
                image_size(mip_width, mip_height, fmt, mip_depth)
                * frames
                * faces
            )

        # First frame, first face, first depth slice.

        file.seek(offset)

        data_size = image_size(width, height, fmt)

        data = file.read(data_size)

        if len(data) != data_size:
            raise ValueError("Недостаточно данных изображения.")

        image = decode_image(data, width, height, fmt)

        info["file_size"] = os.path.getsize(self.filepath)
        info["format_name"] = {
            0: "RGBA8888",
            2: "RGB888",
            3: "BGR888",
            12: "BGRA8888",
            13: "DXT1",
            14: "DXT3",
            15: "DXT5",
            20: "DXT1 ONEBITALPHA"
        }.get(fmt, f"Unknown ({fmt})")

        self.info = info

        return image, info
