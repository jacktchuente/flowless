import datetime as dt
import decimal
import hashlib
import pathlib
import struct
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass, fields


def hash_data(obj, *, algo="sha256", default=None):
    data = _canonical_bytes(obj, seen=set(), default=default)
    return hashlib.new(algo, data).hexdigest()


def _pack(tag, payload=b""):
    tag = tag.encode("utf-8")
    return len(tag).to_bytes(2, "big") + tag + len(payload).to_bytes(8, "big") + payload


def _canonical_bytes(obj, *, seen, default):
    if obj is None:
        return _pack("none")

    if isinstance(obj, bool):
        return _pack("bool", b"1" if obj else b"0")

    if isinstance(obj, int) and not isinstance(obj, bool):
        return _pack("int", str(obj).encode("utf-8"))

    if isinstance(obj, float):
        # Représentation binaire IEEE 754, distingue 0.0 de -0.0.
        return _pack("float", struct.pack("!d", obj))

    if isinstance(obj, str):
        return _pack("str", obj.encode("utf-8"))

    if isinstance(obj, bytes):
        return _pack("bytes", obj)

    if isinstance(obj, decimal.Decimal):
        return _pack("decimal", str(obj).encode("utf-8"))

    if isinstance(obj, (dt.datetime, dt.date, dt.time)):
        return _pack(type(obj).__name__, obj.isoformat().encode("utf-8"))

    if isinstance(obj, uuid.UUID):
        return _pack("uuid", obj.bytes)

    if isinstance(obj, pathlib.Path):
        return _pack("path", str(obj).encode("utf-8"))

    if is_dataclass(obj) and not isinstance(obj, type):
        cls = f"{obj.__class__.__module__}.{obj.__class__.__qualname__}"
        payload = _pack("class", cls.encode("utf-8"))
        for f in fields(obj):
            payload += _canonical_bytes(f.name, seen=seen, default=default)
            payload += _canonical_bytes(getattr(obj, f.name), seen=seen, default=default)
        return _pack("dataclass", payload)

    if isinstance(obj, Mapping):
        obj_id = id(obj)
        if obj_id in seen:
            raise ValueError("Cycle détecté dans le dictionnaire")
        seen.add(obj_id)

        items = []
        for k, v in obj.items():
            kb = _canonical_bytes(k, seen=seen, default=default)
            vb = _canonical_bytes(v, seen=seen, default=default)
            items.append((kb, vb))

        seen.remove(obj_id)

        # Tri canonique par représentation sérialisée de la clé.
        payload = b"".join(kb + vb for kb, vb in sorted(items))
        return _pack("dict", payload)

    if isinstance(obj, (set, frozenset)):
        obj_id = id(obj)
        if obj_id in seen:
            raise ValueError("Cycle détecté dans un set")
        seen.add(obj_id)

        elements = sorted(
            _canonical_bytes(x, seen=seen, default=default)
            for x in obj
        )

        seen.remove(obj_id)
        return _pack(type(obj).__name__, b"".join(elements))

    if isinstance(obj, tuple):
        payload = b"".join(
            _canonical_bytes(x, seen=seen, default=default)
            for x in obj
        )
        return _pack("tuple", payload)

    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        obj_id = id(obj)
        if obj_id in seen:
            raise ValueError("Cycle détecté dans une séquence")
        seen.add(obj_id)

        payload = b"".join(
            _canonical_bytes(x, seen=seen, default=default)
            for x in obj
        )

        seen.remove(obj_id)
        return _pack("list", payload)

    if default is not None:
        return _canonical_bytes(default(obj), seen=seen, default=default)

    raise TypeError(f"Type non supporté pour hash déterministe : {type(obj)!r}")