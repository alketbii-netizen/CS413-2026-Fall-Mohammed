// Wiring: connects buttons, the player (controller) and the board view.
import { RpcClient } from "./rpc-client.js";
import { QueenPlayer } from "./player.js";
import { BoardView, describe } from "./board-view.js";

const $ = (id) => document.getElementById(id);
const view = new BoardView($("board"));
const player = new QueenPlayer(new RpcClient(), onEvent);
let timer = null, busy = false;

function onEvent(ev) {
  view.render(ev);
  const li = document.createElement("li");
  li.textContent = `${player.events}. ${describe(ev)}`; li.className = ev.event;
  $("log").prepend(li);
  while ($("log").children.length > 200) $("log").lastChild.remove();
  $("solutions").textContent = player.solutions;
  $("events").textContent = player.events;
  $("backtracks").textContent = player.backtracks;
  const s = $("status");
  s.classList.toggle("done", ev.event === "done");
  s.textContent = ev.event === "done"
    ? `Search complete: ${player.solutions} solutions. Press Restart to search again.`
    : ev.event === "solution" ? `Solution #${player.solutions} found: [${ev.board}]` : describe(ev);
}

function showError(e) {
  pause();
  $("error").hidden = false;
  $("error").textContent = `RPC failure: ${e.message}. Press Reset or Start to try again.`;
  syncButtons();
}
function clearError() { $("error").hidden = true; $("error").textContent = ""; }

function syncButtons() {
  const active = !!player.streamId && !player.finished;
  $("step").disabled = !active || timer !== null;
  $("play").disabled = !active;
  $("next-solution").disabled = !active || timer !== null;
  $("reset").disabled = !player.streamId;
  $("play").textContent = timer ? "Pause" : "Play";
  $("start").textContent = player.finished ? "Restart" : "Start";
}

async function guarded(fn) {
  if (busy) return;
  busy = true;
  try { clearError(); await fn(); } catch (e) { showError(e); }
  finally { busy = false; syncButtons(); }
}

function pause() { if (timer) { clearTimeout(timer); timer = null; } }
function tick() {
  timer = setTimeout(async () => {
    try { await player.step(); } catch (e) { showError(e); return; }
    if (player.finished) { pause(); syncButtons(); return; }
    if (timer) tick();
  }, Number($("speed").value));
}

$("start").onclick = () => guarded(async () => {
  pause();
  const size = Number($("size").value);
  view.draw(size); $("log").innerHTML = "";
  ["solutions", "events", "backtracks"].forEach((k) => $(k).textContent = "0");
  await player.start(size);
  $("status").classList.remove("done");
  $("status").textContent = `Opened a ${size}×${size} search (nothing computed yet). Step or Play.`;
});
$("step").onclick = () => guarded(() => player.step());
$("next-solution").onclick = () => guarded(() => player.nextSolution());
$("play").onclick = () => { if (timer) pause(); else tick(); syncButtons(); };
$("reset").onclick = () => guarded(async () => {
  pause(); await player.reset(); view.clear(); $("log").innerHTML = "";
  ["solutions", "events", "backtracks"].forEach((k) => $(k).textContent = "0");
  $("status").classList.remove("done");
  $("status").textContent = "Reset. Press Start to open a search.";
});
$("speed").oninput = () => { $("speed-label").textContent = `${$("speed").value} ms`; };
$("size").onchange = () => { if (!player.streamId) view.draw(Number($("size").value)); };
syncButtons();
window.__player = player;   // exposed for automated browser tests
