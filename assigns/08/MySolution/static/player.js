// Controller: pulls events from the server on demand (batches of BATCH),
// keeps a small buffer, and hands each event to a listener.  No DOM access.
export const BATCH = 8;

export class QueenPlayer {
  constructor(rpc, onEvent) {
    this.rpc = rpc; this.onEvent = onEvent;
    this.streamId = null; this.buffer = []; this.serverDone = false;
    this.finished = false; this.solutions = 0; this.events = 0; this.backtracks = 0;
    this.requests = 0;
  }
  async start(size) {
    await this.reset();
    const r = await this.rpc.open(size);
    this.streamId = r.stream_id; this.size = r.size;
  }
  async reset() {
    const id = this.streamId;
    this.streamId = null; this.buffer = []; this.serverDone = false; this.finished = false;
    this.solutions = 0; this.events = 0; this.backtracks = 0;
    if (id && !this.closedByServer) { try { await this.rpc.close(id); } catch (e) { /* already gone */ } }
    this.closedByServer = false;
  }
  // Return the next event, fetching another small batch only if the buffer is empty.
  async step() {
    if (this.finished || !this.streamId) return null;
    if (this.buffer.length === 0 && !this.serverDone) {
      this.requests++;
      const r = await this.rpc.next(this.streamId, BATCH);
      this.buffer.push(...r.events);
      this.serverDone = r.done;
    }
    const ev = this.buffer.shift();
    if (!ev) { this.finished = true; return null; }
    this.events++;
    if (ev.event === "solution") this.solutions++;
    if (ev.event === "backtrack") this.backtracks++;
    if (ev.event === "done") { this.finished = true; this.closedByServer = true; }
    this.onEvent(ev);
    return ev;
  }
  // Advance until (and including) the next solution or done event.
  async nextSolution() {
    let ev;
    do { ev = await this.step(); } while (ev && ev.event !== "solution" && ev.event !== "done");
    return ev;
  }
}
