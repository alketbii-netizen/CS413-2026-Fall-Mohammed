// Transport: JSON-RPC 2.0 over POST /rpc.  No search or rendering logic.
export class RpcError extends Error {
  constructor(message, code = null) { super(message); this.code = code; }
}

export class RpcClient {
  constructor(url = "/rpc", fetchImpl = (...a) => fetch(...a)) {
    this.url = url; this.fetch = fetchImpl; this.nextId = 1;
  }
  async call(method, params) {
    const id = this.nextId++;
    let res;
    try {
      res = await this.fetch(this.url, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", method, params, id }),
      });
    } catch (e) { throw new RpcError("Network error: could not reach the server"); }
    if (!res.ok) throw new RpcError(`HTTP ${res.status} from server`);
    let body;
    try { body = await res.json(); } catch (e) { throw new RpcError("Malformed server response"); }
    if (body.error) throw new RpcError(`${body.error.message} (code ${body.error.code})`, body.error.code);
    if (body.id !== id) throw new RpcError("Response id mismatch");
    return body.result;
  }
  open(size) { return this.call("queens.open", { size }); }
  next(stream_id, limit) { return this.call("queens.next", { stream_id, limit }); }
  close(stream_id) { return this.call("queens.close", { stream_id }); }
}
