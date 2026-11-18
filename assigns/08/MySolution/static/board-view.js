// Rendering: draws the board from each event's snapshot.  No network access.
export class BoardView {
  constructor(root) { this.root = root; this.size = 8; this.draw(8); }
  draw(size) {
    this.size = size;
    this.root.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
    this.root.style.gridTemplateRows = `repeat(${size}, 1fr)`;
    this.root.innerHTML = "";
    this.cells = [];
    for (let r = 0; r < size; r++) {
      const row = [];
      for (let c = 0; c < size; c++) {
        const d = document.createElement("div");
        d.className = "cell " + ((r + c) % 2 ? "dark" : "light");
        d.dataset.row = r; d.dataset.col = c; d.setAttribute("role", "gridcell");
        this.root.appendChild(d); row.push(d);
      }
      this.cells.push(row);
    }
    this.root.classList.remove("solved");
  }
  clear() { this.draw(this.size); }
  showBoard(board) {
    for (const row of this.cells) for (const d of row) d.classList.remove(
      "queen", "try", "place", "reject", "backtrack", "attacker");
    board.forEach((c, r) => this.cells[r][c].classList.add("queen"));
  }
  // Earlier queen attacking (row, col), for explaining a rejection.
  static attacker(board, row, col) {
    for (let r = board.length - 1; r >= 0; r--) {
      const c = board[r], d = row - r;
      if (c === col || c === col - d || c === col + d) return r;
    }
    return -1;
  }
  render(ev) {
    this.root.classList.remove("solved");
    if (ev.event === "done") { return; }
    this.showBoard(ev.board);
    const cell = ev.event === "solution" ? null : this.cells[ev.row][ev.column];
    switch (ev.event) {
      case "try": cell.classList.add("try"); break;
      case "place": cell.classList.add("place"); break;
      case "reject": {
        cell.classList.add("reject");
        const r = BoardView.attacker(ev.board, ev.row, ev.column);
        if (r >= 0) this.cells[r][ev.board[r]].classList.add("attacker");
        break;
      }
      case "backtrack": cell.classList.add("backtrack"); break;
      case "solution": this.root.classList.add("solved"); break;
    }
  }
}

export function describe(ev) {
  const at = `(row ${ev.row}, col ${ev.column})`;
  switch (ev.event) {
    case "try": return `try ${at}`;
    case "place": return `place ${at} → [${ev.board}]`;
    case "reject": {
      const r = BoardView.attacker(ev.board, ev.row, ev.column);
      return `reject ${at}: attacked by queen in row ${r}`;
    }
    case "backtrack": return `backtrack ${at}: no column left below it`;
    case "solution": return `solution [${ev.board}]`;
    case "done": return "done — search complete";
  }
  return ev.event;
}
