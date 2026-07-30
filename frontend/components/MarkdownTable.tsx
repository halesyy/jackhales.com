import { Children, cloneElement, createContext, isValidElement, useContext, type ReactNode } from "react";

/**
 * Article tables.
 *
 * Markdown gives us the columns and, optionally, their alignment. Everything
 * else is inferred here: a column whose every value is a number is right
 * aligned so the digits line up, which is what makes a data table readable.
 * The table itself scrolls inside its own container so a wide one never pushes
 * the page sideways.
 */

/** Mirrors React's `align` attribute so these render straight into `Components`. */
type cellAlignment = "left" | "center" | "right" | "justify" | "char" | undefined;

const numericColumns = createContext<boolean[]>([]);

type hastNode = {
  type?: string;
  tagName?: string;
  value?: string;
  properties?: { align?: string };
  children?: hastNode[];
};

function textOf(node: hastNode | undefined): string {
  if (!node) return "";
  if (node.type === "text") return node.value || "";
  return (node.children || []).map(textOf).join("");
}

function elementChildren(node: hastNode | undefined): hastNode[] {
  return (node?.children || []).filter((child) => child.type === "element");
}

function rowsOf(node: hastNode | undefined): hastNode[] {
  const rows: hastNode[] = [];
  for (const child of elementChildren(node)) {
    if (child.tagName === "tr") rows.push(child);
    else rows.push(...rowsOf(child));
  }
  return rows;
}

/** Currency symbols, thousands separators, percentages and plain decimals all count as numeric. */
function isNumericValue(value: string): boolean {
  return /^[-+(]?\s*[$£€¥]?\s*\d[\d,\s]*(\.\d+)?\s*[%)]?$/.test(value.trim());
}

function findNumericColumns(node: hastNode | undefined): boolean[] {
  const bodyRows = rowsOf(node).filter((row) => elementChildren(row).some((cell) => cell.tagName === "td"));
  if (!bodyRows.length) return [];

  const columnCount = Math.max(...bodyRows.map((row) => elementChildren(row).length));
  return Array.from({ length: columnCount }, (_, column) => {
    const values = bodyRows.map((row) => textOf(elementChildren(row)[column]).trim()).filter(Boolean);
    return values.length > 1 && values.every(isNumericValue);
  });
}

function alignmentClass(align: cellAlignment): string {
  if (align === "center") return "text-center";
  if (align === "right") return "text-right tabular-nums";
  return "text-left";
}

type componentProps = { node?: hastNode; children?: ReactNode; align?: cellAlignment };

export function ArticleTable({ node, children }: componentProps) {
  return (
    <numericColumns.Provider value={findNumericColumns(node)}>
      <div className="my-8 overflow-x-auto rounded-[1.2rem] border border-[color:var(--line)] bg-[color:var(--card)] shadow-[0_16px_42px_rgba(21,35,31,0.08)]">
        <table className="w-full min-w-[34rem] border-collapse text-[0.94rem] leading-[1.6]">{children}</table>
      </div>
    </numericColumns.Provider>
  );
}

export function ArticleTableHead({ children }: componentProps) {
  return <thead className="bg-[color:var(--blue-soft)]">{children}</thead>;
}

/**
 * Resolves each cell's alignment here rather than in the cells themselves,
 * because this is the only place that knows which column a cell sits in.
 *
 * The `:---:` alignment Markdown declares reaches us on the syntax node, not as
 * a React prop, so it is read from there; a numeric column with nothing declared
 * falls back to right so the digits line up. Only element children advance the
 * column counter, because the whitespace between cells is a child too.
 */
export function ArticleTableRow({ node, children }: componentProps) {
  const numeric = useContext(numericColumns);
  const declared = elementChildren(node).map((cell) => cell.properties?.align as cellAlignment);

  let column = 0;
  const cells = Children.map(children, (child) => {
    if (!isValidElement<{ align?: cellAlignment }>(child)) return child;
    const align = declared[column] || (numeric[column] ? "right" : undefined);
    column += 1;
    return cloneElement(child, { align });
  });

  return (
    <tr className="border-b border-[color:var(--line)] last:border-b-0 even:bg-[rgba(21,35,31,0.018)] transition-colors hover:bg-[rgba(255,255,255,0.7)]">
      {cells}
    </tr>
  );
}

export function ArticleTableHeaderCell({ children, align }: componentProps) {
  return (
    <th
      scope="col"
      className={`whitespace-nowrap border-b border-[color:var(--line)] px-4 py-3.5 text-[0.68rem] font-bold uppercase tracking-[0.07em] text-[color:var(--ink)] ${alignmentClass(align)}`}
    >
      {children}
    </th>
  );
}

export function ArticleTableCell({ children, align }: componentProps) {
  return <td className={`px-4 py-3 align-top text-[color:#34423d] ${alignmentClass(align)}`}>{children}</td>;
}
