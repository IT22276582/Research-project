import type { ReactNode } from "react";
import { ConsentEntry } from "../../lib/api";

export interface MetricCardProps {
  title: string;
  value: number | string;
  previousValue?: number;
  trend?: "up" | "down" | "stable";
  trendPercentage?: number;
  historicalData?: { timestamp: Date; value: number }[];
  status?: "normal" | "warning" | "critical";
  onClick?: () => void;
}

export interface ColumnDef<T> {
  key: keyof T;
  title: string;
  sortable?: boolean;
  filterable?: boolean;
  render?: (value: any, item: T) => ReactNode;
  width?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  sortable?: boolean;
  filterable?: boolean;
  pagination?: boolean;
  selectable?: boolean;
  exportable?: boolean;
  onRowClick?: (item: T) => void;
}

export interface EventFilters {
  eventType?: string;
  dateRange?: { start: Date; end: Date };
  severity?: "low" | "medium" | "high";
  search?: string;
}
