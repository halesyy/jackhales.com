/**
 * Reading and writing GitHub-flavoured Markdown tables.
 *
 * The article body stays plain Markdown — the visual table editor is a lens over
 * these functions, never a separate storage format. Anything the editor writes
 * back is padded so the source is still pleasant to edit by hand.
 */

export type tableAlignment = "none" | "left" | "center" | "right";

export type markdownTable = {
  /** First line of the table, inclusive. */
  startLine: number;
  /** Line after the table, exclusive. */
  endLine: number;
  header: string[];
  alignments: tableAlignment[];
  rows: string[][];
};

const minimumDelimiterWidth = 3;
const fencePattern = /^\s*(```|~~~)/;

/** Split a table row on its unescaped pipes. GFM requires a literal pipe in a cell to be `\|`. */
export function splitTableRow(line: string): string[] {
  const cells: string[] = [];
  let current = "";
  let escaped = false;

  for (const character of line.trim()) {
    if (escaped) {
      current += character === "|" ? "\\|" : `\\${character}`;
      escaped = false;
      continue;
    }
    if (character === "\\") {
      escaped = true;
      continue;
    }
    if (character === "|") {
      cells.push(current);
      current = "";
      continue;
    }
    current += character;
  }
  if (escaped) current += "\\";
  cells.push(current);

  // A leading or trailing pipe is conventional and produces an empty edge cell.
  if (cells.length && !cells[0].trim()) cells.shift();
  if (cells.length && !cells[cells.length - 1].trim()) cells.pop();
  return cells.map((cell) => cell.trim());
}

function readAlignment(cell: string): tableAlignment | null {
  const value = cell.trim();
  if (!/^:?-+:?$/.test(value)) return null;
  const start = value.startsWith(":");
  const end = value.endsWith(":");
  if (start && end) return "center";
  if (start) return "left";
  if (end) return "right";
  return "none";
}

/** The `|---|:--:|` row, which is what makes the lines above and below a table at all. */
export function parseDelimiterRow(line: string): tableAlignment[] | null {
  if (!line.includes("-") || !line.includes("|")) return null;
  const cells = splitTableRow(line);
  if (!cells.length) return null;
  const alignments = cells.map(readAlignment);
  return alignments.every((alignment): alignment is tableAlignment => alignment !== null) ? alignments : null;
}

function padCells(cells: string[], columns: number): string[] {
  const padded = cells.slice(0, columns);
  while (padded.length < columns) padded.push("");
  return padded;
}

/** Every table in the document, in source order, ignoring anything inside a code fence. */
export function findTables(markdown: string): markdownTable[] {
  const lines = markdown.split("\n");
  const tables: markdownTable[] = [];
  let openFence = "";
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (openFence) {
      if (line.trim().startsWith(openFence)) openFence = "";
      index += 1;
      continue;
    }
    const fence = fencePattern.exec(line);
    if (fence) {
      openFence = fence[1];
      index += 1;
      continue;
    }

    const alignments = index + 1 < lines.length ? parseDelimiterRow(lines[index + 1]) : null;
    if (!alignments || !line.includes("|")) {
      index += 1;
      continue;
    }

    const columns = Math.max(splitTableRow(line).length, alignments.length);
    const rows: string[][] = [];
    let end = index + 2;
    while (end < lines.length && lines[end].includes("|") && lines[end].trim()) {
      rows.push(padCells(splitTableRow(lines[end]), columns));
      end += 1;
    }

    tables.push({
      startLine: index,
      endLine: end,
      header: padCells(splitTableRow(line), columns),
      alignments: padCells(alignments as string[], columns).map((value) => (value || "none") as tableAlignment),
      rows,
    });
    index = end;
  }

  return tables;
}

/** The table the caret currently sits in, if any. */
export function tableAtOffset(markdown: string, offset: number): markdownTable | null {
  const line = markdown.slice(0, Math.max(0, offset)).split("\n").length - 1;
  return findTables(markdown).find((table) => line >= table.startLine && line < table.endLine) || null;
}

function delimiterCell(alignment: tableAlignment, width: number): string {
  const inner = Math.max(minimumDelimiterWidth, width);
  if (alignment === "center") return `:${"-".repeat(Math.max(1, inner - 2))}:`;
  if (alignment === "left") return `:${"-".repeat(Math.max(2, inner - 1))}`;
  if (alignment === "right") return `${"-".repeat(Math.max(2, inner - 1))}:`;
  return "-".repeat(inner);
}

function displayWidth(value: string): number {
  return [...value].length;
}

/** Render a table back to Markdown with every column padded to a common width. */
export function formatTable(table: markdownTable): string {
  const columns = table.header.length;
  const widths = Array.from({ length: columns }, (_, column) =>
    Math.max(
      minimumDelimiterWidth,
      displayWidth(table.header[column] || ""),
      ...table.rows.map((row) => displayWidth(row[column] || "")),
    ),
  );

  const renderRow = (cells: string[]) =>
    `| ${cells.map((cell, column) => (cell || "").padEnd(widths[column])).join(" | ")} |`;

  return [
    renderRow(table.header),
    `| ${table.alignments.map((alignment, column) => delimiterCell(alignment, widths[column])).join(" | ")} |`,
    ...table.rows.map((row) => renderRow(padCells(row, columns))),
  ].join("\n");
}

/** Swap a table's source lines for a freshly formatted version, leaving the rest of the body untouched. */
export function replaceTable(markdown: string, table: markdownTable, next: markdownTable): string {
  const lines = markdown.split("\n");
  return [...lines.slice(0, table.startLine), ...formatTable(next).split("\n"), ...lines.slice(table.endLine)].join("\n");
}

export function emptyTable(columns = 3, rows = 2): markdownTable {
  return {
    startLine: 0,
    endLine: 0,
    header: Array.from({ length: columns }, (_, column) => `Column ${column + 1}`),
    alignments: Array.from({ length: columns }, () => "none" as tableAlignment),
    rows: Array.from({ length: rows }, () => Array.from({ length: columns }, () => "")),
  };
}

function replaceAt<T>(items: T[], index: number, value: T): T[] {
  return items.map((item, position) => (position === index ? value : item));
}

export function withHeaderCell(table: markdownTable, column: number, value: string): markdownTable {
  return { ...table, header: replaceAt(table.header, column, value) };
}

export function withCell(table: markdownTable, row: number, column: number, value: string): markdownTable {
  return { ...table, rows: replaceAt(table.rows, row, replaceAt(table.rows[row], column, value)) };
}

export function withAlignment(table: markdownTable, column: number, alignment: tableAlignment): markdownTable {
  return { ...table, alignments: replaceAt(table.alignments, column, alignment) };
}

export function withRowAdded(table: markdownTable, afterRow: number): markdownTable {
  const blank = table.header.map(() => "");
  const rows = [...table.rows];
  rows.splice(afterRow + 1, 0, blank);
  return { ...table, rows };
}

export function withRowRemoved(table: markdownTable, row: number): markdownTable {
  if (table.rows.length <= 1) return { ...table, rows: [table.header.map(() => "")] };
  return { ...table, rows: table.rows.filter((_, position) => position !== row) };
}

export function withColumnAdded(table: markdownTable, afterColumn: number): markdownTable {
  const insert = <T,>(items: T[], value: T) => {
    const next = [...items];
    next.splice(afterColumn + 1, 0, value);
    return next;
  };
  return {
    ...table,
    header: insert(table.header, `Column ${table.header.length + 1}`),
    alignments: insert(table.alignments, "none" as tableAlignment),
    rows: table.rows.map((row) => insert(row, "")),
  };
}

export function withColumnRemoved(table: markdownTable, column: number): markdownTable {
  if (table.header.length <= 1) return table;
  const drop = <T,>(items: T[]) => items.filter((_, position) => position !== column);
  return {
    ...table,
    header: drop(table.header),
    alignments: drop(table.alignments),
    rows: table.rows.map(drop),
  };
}
