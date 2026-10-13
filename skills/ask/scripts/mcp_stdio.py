"""A minimal MCP client over stdio for the guard (C3) and the reproduction (C6), declaring what Codex declares.

Plan I7 / A2: the guard's and repro's client declares exactly the capabilities Codex 0.159.3 declares to an MCP
server: no `roots` (chrome-devtools-mcp adds client roots to its allowed write roots, so a `roots` capability would
widen the boundary the guard is meant to prove), elicitation declared and every elicitation request declined. A
`roots/list` request is answered "method not found"; so is any other server request except `ping`.

Messages are newline-delimited JSON-RPC 2.0 (the MCP stdio transport). Every call has its own timeout.
"""
import json
import threading
import time

PROTOCOL_VERSION = "2025-06-18"
CAPABILITIES = {"elicitation": {}}  # no roots, no sampling (Codex 0.159.3; elicitation always declined)
CLIENT_INFO = {"name": "ask-codex-guard", "version": "0"}


class McpError(Exception):
    pass


class McpTimeout(McpError):
    pass


class Client:
    def __init__(self, stdin, stdout, log_limit=65536):
        self.stdin, self.stdout = stdin, stdout
        self.replies, self.lock, self.next_id = {}, threading.Condition(), 0
        self.server_requests = []  # (method, our answer) for every request the server sent us
        self.closed = False
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _send(self, message):
        data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
        with self.lock:
            self.stdin.write(data)
            self.stdin.flush()

    def _answer(self, message):
        method = message.get("method")
        if method == "elicitation/create":
            answer = {"result": {"action": "decline"}}
        elif method == "ping":
            answer = {"result": {}}
        else:  # roots/list (roots not declared), sampling and anything else
            answer = {"error": {"code": -32601, "message": f"Method not found: {method}"}}
        self.server_requests.append((method, answer))
        try:
            self._send({"jsonrpc": "2.0", "id": message["id"], **answer})
        except (OSError, ValueError):
            pass

    def _read(self):
        try:
            for line in self.stdout:
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(message, dict):
                    continue
                if "method" in message and "id" in message:
                    self._answer(message)
                elif "id" in message:
                    with self.lock:
                        self.replies[message["id"]] = message
                        self.lock.notify_all()
        except (OSError, ValueError):
            pass
        finally:
            with self.lock:
                self.closed = True
                self.lock.notify_all()

    def request(self, method, params=None, timeout=60):
        with self.lock:
            self.next_id += 1
            ident = self.next_id
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        try:
            self._send(message)
        except (OSError, ValueError) as error:
            raise McpError(f"The MCP server's input is closed ({type(error).__name__})") from None
        deadline = time.monotonic() + timeout
        with self.lock:
            while ident not in self.replies:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise McpTimeout(f"{method}: no answer within {timeout} s")
                if self.closed:
                    raise McpError(f"{method}: the MCP server closed its output")
                self.lock.wait(min(left, 0.5))
            reply = self.replies.pop(ident)
        if "error" in reply:
            raise McpError(f"{method}: {reply['error'].get('message', reply['error'])}")
        return reply.get("result")

    def notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)

    def initialize(self, timeout=90):
        result = self.request("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": CAPABILITIES,
                                             "clientInfo": CLIENT_INFO}, timeout=timeout)
        self.notify("notifications/initialized")
        return result

    def tool(self, name, arguments, timeout=60):
        """(is_error, text) of a tools/call; a protocol-level error is (True, message)."""
        try:
            result = self.request("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
        except McpTimeout:
            raise
        except McpError as error:
            return True, str(error)
        text = "\n".join(item.get("text", "") for item in (result or {}).get("content", [])
                         if isinstance(item, dict) and item.get("type") == "text")
        return bool((result or {}).get("isError")), text
