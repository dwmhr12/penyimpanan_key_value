import os
import struct
import psutil
import pickle
import logging
import time
from collections import OrderedDict
from core.encoder import Encoder, EncoderError

class StorageError(Exception):
    pass

class Storage:
    def __init__(self, cold_storage_path, max_memory_ratio=0.5, avg_item_size=1024):
        self.hot = OrderedDict()
        self.max_memory_ratio = max_memory_ratio
        self.avg_item_size = avg_item_size
        self.hot_limit = self._calculate_hot_limit()
        self.cold_path = cold_storage_path
        self.cold_file = os.path.join(cold_storage_path, "data.bin")
        self.index = {}
        os.makedirs(cold_storage_path, exist_ok=True)
        if not self._load_index():
            self._build_index()
        logging.info(f"Storage initialized: {self.cold_path}, hot limit: {self.hot_limit}")

    def _calculate_hot_limit(self):
        available_memory = psutil.virtual_memory().available
        max_memory = available_memory * self.max_memory_ratio
        return max(10, int(max_memory // self.avg_item_size))

    def _load_index(self):
        index_file = os.path.join(self.cold_path, "index.bin")
        if os.path.exists(index_file):
            with open(index_file, "rb") as f:
                self.index = pickle.load(f)
            logging.info(f"Loaded index from {index_file}")
            return True
        return False

    def _save_index(self):
        index_file = os.path.join(self.cold_path, "index.bin")
        with open(index_file, "wb") as f:
            pickle.dump(self.index, f)
        logging.debug(f"Saved index to {index_file}")

    def _build_index(self):
        if not os.path.exists(self.cold_file):
            return
        self.index.clear()
        with open(self.cold_file, "rb") as f:
            while True:
                offset = f.tell()
                version_data = f.read(1)
                if not version_data:
                    break
                try:
                    schema_version = struct.unpack("!B", version_data)[0]
                    if schema_version == 1:
                        key_len = struct.unpack("!I", f.read(4))[0]
                        key = f.read(key_len).decode("utf-8")
                        value_len = struct.unpack("!I", f.read(4))[0]
                        f.seek(value_len, os.SEEK_CUR)
                    elif schema_version == 2:
                        key_len, value_len, extra_len = struct.unpack("!III", f.read(12))
                        key = f.read(key_len).decode("utf-8")
                        f.seek(value_len + extra_len, os.SEEK_CUR)
                    else:
                        f.seek(offset + 1)
                        continue
                    self.index[key] = offset
                except Exception:
                    f.seek(offset + 1)
                    continue
        self._save_index()

    def _write_cold(self, key, value, schema_version=1, extra_field=None):
        record = Encoder.encode(key, value, schema_version, extra_field)
        offset = os.path.getsize(self.cold_file) if os.path.exists(self.cold_file) else 0
        with open(self.cold_file, "ab") as f:
            f.write(record)
            f.flush()
        self.index[key] = offset
        self._save_index()

    def put(self, key, value, write_to_cold=True, schema_version=1, extra_field=None):
        try:
            if key in self.hot:
                old_value = self.hot[key]
                hist_key = f"{key}::hist{int(time.time() * 1000)}"
                self._write_cold(hist_key, old_value, schema_version, extra_field)
                self.clean_old_versions(key)
            if len(self.hot) >= self.hot_limit:
                evicted_key = next(iter(self.hot))
                evicted_value = self.hot.pop(evicted_key)
                self._write_cold(evicted_key, evicted_value)
            self.hot[key] = value
            if write_to_cold:
                self._write_cold(key, value, schema_version, extra_field)
            logging.info(f"Put key {key}")
        except Exception as e:
            raise StorageError(f"Failed to put {key}: {e}")

    def get(self, key):
        if key in self.hot:
            self.hot.move_to_end(key)
            return self.hot[key]
        if key in self.index:
            with open(self.cold_file, "rb") as f:
                f.seek(self.index[key])
                _, value, _, _ = Encoder.decode(f.read())
                self.hot[key] = value
                return value
        return None

    def get_raw(self, key):
        if key in self.hot:
            return key, self.hot[key], 1, None
        if key in self.index:
            with open(self.cold_file, "rb") as f:
                f.seek(self.index[key])
                return Encoder.decode(f.read())
        return None

    def get_all_versions(self, key):
        result = {}

        # Tambahkan 'latest' dari hot kalau ada
        if key in self.hot:
            result['latest'] = self.hot[key]
        elif key in self.index:
            result['latest'] = self.get(key)

        # Tambahkan histori dari cold
        prefix = f"{key}::hist"
        for hist_key in sorted(k for k in self.index if k.startswith(prefix)):
            with open(self.cold_file, "rb") as f:
                f.seek(self.index[hist_key])
                _, value, _, _ = Encoder.decode(f.read())
                result[hist_key] = value

        return result

    def clean_old_versions(self, key, max_versions=5):
        prefix = f"{key}::hist"
        versions = [k for k in self.index if k.startswith(prefix)]
        if len(versions) > max_versions:
            versions.sort()
            to_remove = versions[:-max_versions]
            for old in to_remove:
                if old in self.index:
                    del self.index[old]
            self._save_index()
            logging.info(f"Cleaned {len(to_remove)} old versions of '{key}'")

    def day_change(self):
        flushed = 0
        for key in list(self.hot.keys()):
            value = self.hot.pop(key)
            self._write_cold(key, value)
            flushed += 1
        return flushed
