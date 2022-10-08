import io
import json
import struct
import sys


def json_encode(obj, encoding):
    return json.dumps(obj, ensure_ascii=False).encode(encoding)


def json_decode(json_bytes, encoding):
    with io.TextIOWrapper(io.BytesIO(json_bytes), encoding=encoding, newline="") as tiow:
        obj = json.load(tiow)
    return obj


def create_message(content, content_type, content_encoding):
    if content_type == "text/json":
        req = {
            "content_bytes": json_encode(content, content_encoding),
            "content_type": content_type,
            "content_encoding": content_encoding,
        }
    else:
        req = {
            "content_bytes": content,
            "content_type": content_type,
            "content_encoding": content_encoding,
        }
    return _create_message(**req)


def _create_message(*, content_bytes, content_type, content_encoding):
    json_header = {
        "byteorder": sys.byteorder,
        "content-type": content_type,
        "content-encoding": content_encoding,
        "content-length": len(content_bytes),
    }
    json_header_bytes = json_encode(json_header, "utf-8")
    # network use bigIndian
    message_hdr = struct.pack(">H", len(json_header_bytes))
    message = message_hdr + json_header_bytes + content_bytes
    return message


def unpack_message(message):
    header_len = 2
    total_len = len(message)
    json_header = None
    content = None
    if total_len >= header_len:
        json_header_len = struct.unpack(">H", message[:header_len])[0]
        if total_len >= header_len + json_header_len:
            header_bytes = message[header_len: header_len + json_header_len]
            json_header = json_decode(header_bytes, "utf-8")

            content_bytes = message[header_len + json_header_len:]
            content_type = json_header["content-type"]
            content_encoding = json_header["content-encoding"]
            if content_type == "text/json":
                content = json_decode(content_bytes, content_encoding)
            else:
                content = content_bytes
    return json_header, content
