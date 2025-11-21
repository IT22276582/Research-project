"use client";

import React, { useMemo, useState } from "react";
import styles from "./DataTable.module.css";
import { DataTableProps } from "../types";

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  sortable = true,
  filterable = true,
  pagination = true,
  selectable = false,
  exportable = false,
  onRowClick,
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{ key: keyof T; direction: "asc" | "desc" } | null>(null);
  const [filterText, setFilterText] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const itemsPerPage = 10;

  const handleSort = (key: keyof T) => {
    if (!sortable) return;
    let direction: "asc" | "desc" = "asc";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
  };

  const filteredData = useMemo(() => {
    if (!filterable || !filterText) return data;
    return data.filter((item) =>
      columns.some((column) => {
        const value = item[column.key];
        return value && value.toString().toLowerCase().includes(filterText.toLowerCase());
      }),
    );
  }, [data, columns, filterText, filterable]);

  const sortedData = useMemo(() => {
    if (!sortConfig) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;
      if (aValue < bValue) return sortConfig.direction === "asc" ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });
  }, [filteredData, sortConfig]);

  const totalPages = Math.max(1, Math.ceil(sortedData.length / itemsPerPage));
  const paginatedData = pagination
    ? sortedData.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage)
    : sortedData;

  const toggleRow = (index: number) => {
    if (!selectable) return;
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(sortedData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "table-export.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={styles.container}>
      {(filterable || exportable) && (
        <div className={styles.controls}>
          {filterable && (
            <input
              className={styles.search}
              placeholder="Filter rows..."
              value={filterText}
              onChange={(event) => {
                setCurrentPage(1);
                setFilterText(event.target.value);
              }}
            />
          )}
          {exportable && (
            <button
              type="button"
              onClick={handleExport}
              className="rounded-full border border-slate-700/60 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-800/40"
            >
              Export JSON
            </button>
          )}
        </div>
      )}
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              {selectable && <th className={styles.th}>Select</th>}
              {columns.map((column) => (
                <th
                  key={column.title}
                  className={styles.th}
                  style={{ width: column.width }}
                  onClick={() => column.sortable !== false && handleSort(column.key)}
                >
                  {column.title}
                  {sortConfig?.key === column.key && (sortConfig.direction === "asc" ? " ▲" : " ▼")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td className={`${styles.td}`} colSpan={columns.length + (selectable ? 1 : 0)}>
                  No data available
                </td>
              </tr>
            ) : (
              paginatedData.map((item, rowIndex) => {
                const absoluteIndex = pagination ? (currentPage - 1) * itemsPerPage + rowIndex : rowIndex;
                return (
                  <tr
                    key={absoluteIndex}
                    className={styles.row}
                    onClick={() => onRowClick?.(item)}
                  >
                    {selectable && (
                      <td className={styles.td}>
                        <input
                          type="checkbox"
                          className={styles.checkbox}
                          checked={selectedRows.has(absoluteIndex)}
                          onChange={() => toggleRow(absoluteIndex)}
                        />
                      </td>
                    )}
                    {columns.map((column) => (
                      <td key={String(column.key)} className={styles.td}>
                        {column.render ? column.render(item[column.key], item) : String(item[column.key] ?? "")}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      {pagination && (
        <div className={styles.pagination}>
          <div>
            Page {currentPage} / {totalPages}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="rounded-full border border-slate-700/60 px-3 py-1 text-xs disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="rounded-full border border-slate-700/60 px-3 py-1 text-xs disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
