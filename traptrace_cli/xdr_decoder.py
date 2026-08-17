"""
Soroban XDR Decoder and Diagnostic Event Parser.
Decodes base64-encoded XDR structures, DiagnosticEvents, SCVal objects, and call traces.
"""

import base64
import struct
from typing import Dict, Any, List, Optional, Tuple, Union

# SCVal Type Enum Constants in Stellar/Soroban
SCV_BOOL = 0
SCV_VOID = 1
SCV_ERROR = 2
SCV_U32 = 3
SCV_I32 = 4
SCV_U64 = 5
SCV_I64 = 6
SCV_TIMEPOINT = 7
SCV_DURATION = 8
SCV_U128 = 9
SCV_I128 = 10
SCV_U256 = 11
SCV_I256 = 12
SCV_BYTES = 13
SCV_STRING = 14
SCV_SYMBOL = 15
SCV_VEC = 16
SCV_MAP = 17
SCV_ADDRESS = 18
SCV_CONTRACT_INSTANCE = 19
SCV_LEDGER_KEY_CONTRACT_INSTANCE = 20
SCV_LEDGER_KEY_NONCE = 21

# SCError Type Enum Constants
SCE_CONTRACT = 0
SCE_STORAGE = 1
SCE_CONTEXT = 2
SCE_CRYPTO = 3
SCE_EVENTS = 4
SCE_BUDGET = 5
SCE_AUTH = 6
SCE_WASM_VM = 7

SCE_TYPE_NAMES = {
    SCE_CONTRACT: "ContractError",
    SCE_STORAGE: "StorageError",
    SCE_CONTEXT: "ContextError",
    SCE_CRYPTO: "CryptoError",
    SCE_EVENTS: "EventsError",
    SCE_BUDGET: "BudgetError",
    SCE_AUTH: "AuthError",
    SCE_WASM_VM: "WasmVmError"
}

# ContractEvent Types
CONTRACT_EVENT_TYPE_SYSTEM = 0
CONTRACT_EVENT_TYPE_CONTRACT = 1
CONTRACT_EVENT_TYPE_DIAGNOSTIC = 2

CONTRACT_EVENT_TYPE_NAMES = {
    CONTRACT_EVENT_TYPE_SYSTEM: "SYSTEM",
    CONTRACT_EVENT_TYPE_CONTRACT: "CONTRACT",
    CONTRACT_EVENT_TYPE_DIAGNOSTIC: "DIAGNOSTIC"
}

class XdrReader:
    """Stream reader for binary XDR decoding."""
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read_int(self) -> int:
        if self.remaining() < 4:
            raise ValueError("Unexpected EOF reading int32")
        val = struct.unpack(">i", self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return val

    def read_uint(self) -> int:
        if self.remaining() < 4:
            raise ValueError("Unexpected EOF reading uint32")
        val = struct.unpack(">I", self.data[self.offset:self.offset+4])[0]
        self.offset += 4
        return val

    def read_int64(self) -> int:
        if self.remaining() < 8:
            raise ValueError("Unexpected EOF reading int64")
        val = struct.unpack(">q", self.data[self.offset:self.offset+8])[0]
        self.offset += 8
        return val

    def read_uint64(self) -> int:
        if self.remaining() < 8:
            raise ValueError("Unexpected EOF reading uint64")
        val = struct.unpack(">Q", self.data[self.offset:self.offset+8])[0]
        self.offset += 8
        return val

    def read_bool(self) -> bool:
        return self.read_int() != 0

    def read_opaque(self, length: int) -> bytes:
        if self.remaining() < length:
            raise ValueError(f"Unexpected EOF reading opaque bytes of length {length}")
        val = self.data[self.offset:self.offset+length]
        self.offset += length
        # XDR 4-byte padding
        padding = (4 - (length % 4)) % 4
        self.offset += padding
        return val

    def read_var_opaque(self, max_length: int = 1000000) -> bytes:
        length = self.read_uint()
        if length > max_length:
            raise ValueError(f"Opaque size {length} exceeds maximum {max_length}")
        return self.read_opaque(length)

    def read_string(self) -> str:
        raw = self.read_var_opaque()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin1", errors="replace")


def decode_scval(reader: XdrReader, depth: int = 0) -> Any:
    """Recursively decodes a Soroban SCVal object."""
    if depth > 50:
        return "<max-depth-exceeded>"
    
    val_type = reader.read_int()
    
    if val_type == SCV_BOOL:
        return reader.read_bool()
    elif val_type == SCV_VOID:
        return None
    elif val_type == SCV_ERROR:
        err_type = reader.read_int()
        code = reader.read_uint()
        type_name = SCE_TYPE_NAMES.get(err_type, f"ErrorType({err_type})")
        return {"error_type": type_name, "code": code}
    elif val_type == SCV_U32:
        return reader.read_uint()
    elif val_type == SCV_I32:
        return reader.read_int()
    elif val_type == SCV_U64:
        return reader.read_uint64()
    elif val_type == SCV_I64:
        return reader.read_int64()
    elif val_type in (SCV_TIMEPOINT, SCV_DURATION):
        return reader.read_uint64()
    elif val_type == SCV_U128:
        hi = reader.read_uint64()
        lo = reader.read_uint64()
        return (hi << 64) | lo
    elif val_type == SCV_I128:
        hi = reader.read_int64()
        lo = reader.read_uint64()
        return (hi << 64) | lo
    elif val_type in (SCV_U256, SCV_I256):
        raw = reader.read_opaque(32)
        return int.from_bytes(raw, byteorder="big", signed=(val_type == SCV_I256))
    elif val_type == SCV_BYTES:
        raw = reader.read_var_opaque()
        return f"0x{raw.hex()}"
    elif val_type == SCV_STRING:
        return reader.read_string()
    elif val_type == SCV_SYMBOL:
        return reader.read_string()
    elif val_type == SCV_VEC:
        has_vec = reader.read_bool()
        if not has_vec:
            return []
        count = reader.read_uint()
        return [decode_scval(reader, depth + 1) for _ in range(min(count, 500))]
    elif val_type == SCV_MAP:
        has_map = reader.read_bool()
        if not has_map:
            return {}
        count = reader.read_uint()
        res = {}
        for _ in range(min(count, 500)):
            k = decode_scval(reader, depth + 1)
            v = decode_scval(reader, depth + 1)
            res[str(k)] = v
        return res
    elif val_type == SCV_ADDRESS:
        addr_type = reader.read_int()
        if addr_type == 0:  # Account
            raw = reader.read_opaque(32)
            return f"G{raw.hex()[:10]}..."
        elif addr_type == 1:  # Contract
            raw = reader.read_opaque(32)
            return f"C{raw.hex()[:10]}..."
        return f"<Address type={addr_type}>"
    else:
        return f"<SCVal type={val_type}>"


def decode_diagnostic_event(b64_xdr: str) -> Dict[str, Any]:
    """
    Decodes a base64-encoded DiagnosticEvent XDR.
    Structure:
      in_successful_contract_call: bool
      event: ContractEvent (ext: int, contract_id: optional bytes32, type: int, body: v0(topics: vec, data: scval))
    """
    try:
        raw_bytes = base64.b64decode(b64_xdr)
    except Exception as e:
        return {"error": f"Base64 decode failure: {e}", "raw": b64_xdr}

    reader = XdrReader(raw_bytes)
    try:
        in_success = reader.read_bool()
        
        # ContractEvent
        reader.read_int() # ext
        has_contract_id = reader.read_bool()
        contract_id = None
        if has_contract_id:
            contract_id = f"C{reader.read_opaque(32).hex()}"
        
        event_type = reader.read_int()
        event_type_name = CONTRACT_EVENT_TYPE_NAMES.get(event_type, f"TYPE_{event_type}")

        body_version = reader.read_int()
        topics = []
        data = None

        if body_version == 0:
            num_topics = reader.read_uint()
            for _ in range(num_topics):
                topics.append(decode_scval(reader))
            data = decode_scval(reader)

        return {
            "in_successful_call": in_success,
            "contract_id": contract_id,
            "event_type": event_type_name,
            "topics": topics,
            "data": data
        }
    except Exception as e:
        # Fallback if standard DiagnosticEvent parser hits variance
        return {
            "in_successful_call": False,
            "error": f"Partial XDR parse: {str(e)}",
            "raw_hex": raw_bytes.hex()
        }


def parse_diagnostic_events_list(events_list: List[Union[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Parses a collection of diagnostic events (either base64 XDR strings or pre-parsed dicts)."""
    parsed = []
    for ev in events_list:
        if isinstance(ev, str):
            parsed.append(decode_diagnostic_event(ev))
        elif isinstance(ev, dict) and "xdr" in ev:
            parsed.append(decode_diagnostic_event(ev["xdr"]))
        elif isinstance(ev, dict):
            parsed.append(ev)
    return parsed


def extract_trace_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extracts high-level execution trace, function calls, traps, host errors,
    and resource/budget metrics from decoded diagnostic events.
    """
    calls = []
    errors = []
    auth_events = []
    metrics = {}

    for ev in events:
        topics = ev.get("topics", [])
        data = ev.get("data")
        
        if not topics:
            continue

        topic_strs = [str(t) for t in topics]
        
        # Function call
        if topic_strs[0] == "fn_call":
            func_name = topic_strs[1] if len(topic_strs) > 1 else "<unknown>"
            contract = ev.get("contract_id", "<host>")
            calls.append({"contract": contract, "function": func_name, "args": data})

        # Error / Trap
        elif "error" in topic_strs or "trap" in topic_strs or (isinstance(data, dict) and "error_type" in data):
            errors.append({
                "contract": ev.get("contract_id"),
                "topics": topic_strs,
                "detail": data
            })

        # Auth tree verification
        elif "auth" in topic_strs:
            auth_events.append({"topics": topic_strs, "detail": data})

        # Resource consumption metrics
        elif "core_metrics" in topic_strs:
            if isinstance(data, dict):
                metrics.update(data)

    return {
        "call_count": len(calls),
        "calls": calls,
        "error_count": len(errors),
        "errors": errors,
        "auth_events": auth_events,
        "metrics": metrics
    }
