import { AlignCenter, AlignLeft, AlignRight, Columns3, Plus, Rows3, Trash2, X } from "lucide-react";
import { useState } from "react";

import {
  formatTable,
  withAlignment,
  withCell,
  withColumnAdded,
  withColumnRemoved,
  withHeaderCell,
  withRowAdded,
  withRowRemoved,
  type markdownTable,
  type tableAlignment,
} from "../lib/markdownTable";

type tableBuilderProps = {
  table: markdownTable;
  mode: "insert" | "edit";
  onApply: (table: markdownTable) => void;
  onCancel: () => void;
};

const alignmentChoices: { value: tableAlignment; label: string; icon: typeof AlignLeft }[] = [
  { value: "left", label: "Align left", icon: AlignLeft },
  { value: "center", label: "Align centre", icon: AlignCenter },
  { value: "right", label: "Align right", icon: AlignRight },
];

/**
 * A grid over the Markdown, not a replacement for it.
 *
 * Editing happens on a parsed table and is written straight back as padded GFM,
 * so a table built here is still an ordinary Markdown table that can be edited
 * by hand afterwards — or by the content API.
 */
export function TableBuilder({ table, mode, onApply, onCancel }: tableBuilderProps) {
  const [draft, setDraft] = useState(table);

  return (
    <div className="table-builder">
      <div className="table-builder-heading">
        <div>
          <p className="eyebrow">{mode === "insert" ? "New table" : "Edit table"}</p>
          <h3>{draft.header.length} columns · {draft.rows.length} rows</h3>
        </div>
        <button type="button" className="table-builder-close" title="Close" onClick={onCancel}><X size={16} /></button>
      </div>

      <div className="table-builder-scroll">
        <table className="table-builder-grid">
          <thead>
            <tr>
              <th aria-hidden="true" />
              {draft.header.map((heading, column) => (
                <th key={column}>
                  <input
                    value={heading}
                    aria-label={`Heading for column ${column + 1}`}
                    placeholder={`Column ${column + 1}`}
                    onChange={(event) => setDraft(withHeaderCell(draft, column, event.target.value))}
                  />
                  <div className="table-builder-column-tools">
                    {alignmentChoices.map(({ value, label, icon: Icon }) => (
                      <button
                        key={value}
                        type="button"
                        title={label}
                        aria-pressed={draft.alignments[column] === value}
                        className={draft.alignments[column] === value ? "is-active" : undefined}
                        onClick={() =>
                          setDraft(withAlignment(draft, column, draft.alignments[column] === value ? "none" : value))
                        }
                      >
                        <Icon size={13} />
                      </button>
                    ))}
                    <button type="button" title="Add a column after this one" onClick={() => setDraft(withColumnAdded(draft, column))}>
                      <Plus size={13} />
                    </button>
                    <button
                      type="button"
                      title="Remove this column"
                      disabled={draft.header.length <= 1}
                      onClick={() => setDraft(withColumnRemoved(draft, column))}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {draft.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                <td className="table-builder-row-tools">
                  <button type="button" title="Add a row below" onClick={() => setDraft(withRowAdded(draft, rowIndex))}>
                    <Plus size={13} />
                  </button>
                  <button type="button" title="Remove this row" onClick={() => setDraft(withRowRemoved(draft, rowIndex))}>
                    <Trash2 size={13} />
                  </button>
                </td>
                {draft.header.map((_, column) => (
                  <td key={column}>
                    <input
                      value={row[column] || ""}
                      aria-label={`Row ${rowIndex + 1}, column ${column + 1}`}
                      onChange={(event) => setDraft(withCell(draft, rowIndex, column, event.target.value))}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-builder-add">
        <button type="button" className="button button-outline" onClick={() => setDraft(withRowAdded(draft, draft.rows.length - 1))}>
          <Rows3 size={15} /> Add row
        </button>
        <button type="button" className="button button-outline" onClick={() => setDraft(withColumnAdded(draft, draft.header.length - 1))}>
          <Columns3 size={15} /> Add column
        </button>
      </div>

      <details className="table-builder-source">
        <summary>Markdown it will write</summary>
        <pre>{formatTable(draft)}</pre>
      </details>

      <div className="table-builder-actions">
        <button type="button" className="button button-outline" onClick={onCancel}>Cancel</button>
        <button type="button" className="button button-dark" onClick={() => onApply(draft)}>
          {mode === "insert" ? "Insert table" : "Update table"}
        </button>
      </div>
    </div>
  );
}
