import hashlib
import logging
import threading
from core.storage import Storage

class ShardManager:
    def __init__(self, num_shards=2, replica_count=2):
        self.num_shards = num_shards
        self.replica_count = replica_count
        self.shards = []
        self.async_queue = []
        self.async_thread = None

        for shard_id in range(num_shards):
            shard = []
            for replica_id in range(replica_count):
                cold_path = f"data/cold_store/shard{shard_id}_rep{replica_id}"
                storage = Storage(cold_path)
                shard.append(storage)
            self.shards.append(shard)

        self._start_async_replication()
        logging.info(f"ShardManager initialized: {num_shards} shards, {replica_count} replicas")

    def _get_shard_id(self, key):
        return int(hashlib.sha256(key.encode()).hexdigest(), 16) % self.num_shards

    def _start_async_replication(self):
        self.async_thread = threading.Thread(target=self._async_replication_worker, daemon=True)
        self.async_thread.start()

    def _async_replication_worker(self):
        while True:
            if self.async_queue:
                key, value, write_to_cold, shard_id, schema_version, extra_field = self.async_queue.pop(0)
                for replica in self.shards[shard_id][1:]:
                    replica.put(key, value, write_to_cold, schema_version, extra_field)
                    logging.debug(f"Async replicated key {key} to shard{shard_id}")

    def put(self, key, value, write_to_cold=True, async_replication=False, schema_version=1, extra_field=None):
        shard_id = self._get_shard_id(key)
        if async_replication:
            self.shards[shard_id][0].put(key, value, write_to_cold, schema_version, extra_field)
            self.async_queue.append((key, value, write_to_cold, shard_id, schema_version, extra_field))
            logging.debug(f"Putting key {key} async on shard {shard_id}")
        else:
            for replica_id, replica in enumerate(self.shards[shard_id]):
                replica.put(key, value, write_to_cold, schema_version, extra_field)
                logging.debug(f"Put key {key} to shard {shard_id}, replica {replica_id}")

    def get(self, key):
        shard_id = self._get_shard_id(key)
        for replica_id, replica in enumerate(self.shards[shard_id]):
            try:
                value = replica.get(key)
                if value is not None:
                    logging.info(f"Retrieved key {key} from shard {shard_id}, replica {replica_id}")
                    return value
            except Exception as e:
                logging.warning(f"Replica {replica_id} of shard {shard_id} failed get({key}): {e}")
        logging.error(f"Key {key} not found in any replica of shard {shard_id}")
        return None

    def day_change(self):
        flushed = {}
        for shard_id, shard in enumerate(self.shards):
            flushed[shard_id] = []
            for replica in shard:
                count = replica.day_change()
                flushed[shard_id].append(count)
        return flushed

    def check_replica_consistency(self, key):
        shard_id = self._get_shard_id(key)
        values = []
        for replica_id, replica in enumerate(self.shards[shard_id]):
            try:
                values.append(replica.get(key))
            except:
                values.append(None)
        unique = set(str(v) for v in values)
        if len(unique) == 1:
            logging.info(f"Key {key} consistent on shard {shard_id}")
            return True
        logging.warning(f"Inconsistent replicas for {key} on shard {shard_id}: {values}")
        return False
