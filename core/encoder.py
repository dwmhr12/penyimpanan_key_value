import struct
import zlib
import json
import logging
from datetime import datetime

class EncoderError(Exception):
    """Exception raised for errors in encoding/decoding operations."""
    pass

class Encoder:
    @staticmethod
    def encode(key, value, schema_version=1, extra_field=None):
        """
        Encode a key-value pair into a binary format.

        Args:
            key (str): The key to encode.
            value (dict): The value to encode (JSON-serializable).
            schema_version (int): Schema version (1–4).
            extra_field (str, optional): Additional field for extended schema.

        Returns:
            bytes: Encoded binary data.
        """
        try:
            key_bytes = key.encode("utf-8")
            key_len = len(key_bytes)
            value_json = json.dumps(value)
            value_compressed = zlib.compress(value_json.encode("utf-8"))
            value_len = len(value_compressed)
            extra_bytes = extra_field.encode("utf-8") if extra_field else b""
            extra_len = len(extra_bytes)

            if schema_version in (1,):
                return struct.pack("!BII", 1, key_len, value_len) + key_bytes + value_compressed

            elif schema_version in (2, 3, 4):
                return struct.pack("!BIII", schema_version, key_len, value_len, extra_len) + key_bytes + value_compressed + extra_bytes

            else:
                raise EncoderError(f"Unsupported schema version: {schema_version}")

        except Exception as e:
            raise EncoderError(f"Failed to encode {key}: {e}")

    @staticmethod
    def decode(data):
        """
        Decode a binary record into a key-value pair and schema version.

        Args:
            data (bytes): Binary data to decode.

        Returns:
            tuple: (key, value, schema_version, extra_field)
        """
        try:
            schema_version = struct.unpack("!B", data[:1])[0]

            if schema_version == 1:
                key_len, value_len = struct.unpack("!II", data[1:9])
                key = data[9:9+key_len].decode("utf-8")
                value_compressed = data[9+key_len:9+key_len+value_len]
                value = json.loads(zlib.decompress(value_compressed).decode("utf-8"))
                return key, value, schema_version, None

            elif schema_version in (2, 3, 4):
                key_len, value_len, extra_len = struct.unpack("!III", data[1:13])
                key = data[13:13+key_len].decode("utf-8")
                value_compressed = data[13+key_len:13+key_len+value_len]
                value = json.loads(zlib.decompress(value_compressed).decode("utf-8"))
                extra_field = (
                    data[13+key_len+value_len:13+key_len+value_len+extra_len].decode("utf-8")
                    if extra_len > 0 else None
                )
                return key, value, schema_version, extra_field

            else:
                raise EncoderError(f"Unsupported schema version: {schema_version}")

        except Exception as e:
            raise EncoderError(f"Failed to decode: {e}")

    @staticmethod
    def add_version_to_key(key):
        """Tambahkan timestamp ke key untuk menyimpan versi histori."""
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        return f"{key}::{timestamp}"
