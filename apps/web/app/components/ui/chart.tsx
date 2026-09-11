"use client";

import * as React from "react";
import {
  Bar,
  BarChart as ReBarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart as RePieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";

// Chart layer: shadcn Chart encapsulation over Recharts v3.
// Ref: https://ui.shadcn.com/docs/components/base/chart (ChartContainer / Tooltip / Legend pattern)
// Palette locked to zinc + emerald/amber.
const PALETTE = ["#10b981", "#3f3f46", "#f59e0b", "#71717a", "#059669", "#a1a1aa"];

export function ChartContainer({
  title,
  description,
  className,
  children,
}: {
  title?: string;
  description?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className={className}>
      {(title || description) && (
        <CardHeader>
          {title && <CardTitle className="text-sm">{title}</CardTitle>}
          {description && <CardDescription className="text-xs">{description}</CardDescription>}
        </CardHeader>
      )}
      <CardContent>
        <div className="h-64 w-full">{children}</div>
      </CardContent>
    </Card>
  );
}

export function CompareBarChart({
  data,
  bars,
  title,
  description,
}: {
  data: Record<string, string | number>[];
  bars: { key: string; label: string; color?: string }[];
  title?: string;
  description?: string;
}) {
  return (
    <ChartContainer title={title} description={description}>
      <ResponsiveContainer width="100%" height="100%">
        <ReBarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#71717a" }} tickLine={false} axisLine={{ stroke: "#e4e4e7" }} />
          <YAxis tick={{ fontSize: 11, fill: "#71717a" }} tickLine={false} axisLine={false} domain={[0, 100]} />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: "1px solid #e4e4e7", fontSize: 12 }}
            formatter={(value) => [`${value}%`, ""]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {bars.map((b, i) => (
            <Bar key={b.key} dataKey={b.key} name={b.label} fill={b.color ?? PALETTE[i % PALETTE.length]} radius={[6, 6, 0, 0]} maxBarSize={44} />
          ))}
        </ReBarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

export function DonutChart({
  data,
  title,
  description,
}: {
  data: { name: string; value: number }[];
  title?: string;
  description?: string;
}) {
  return (
    <ChartContainer title={title} description={description}>
      <ResponsiveContainer width="100%" height="100%">
        <RePieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={52} outerRadius={80} paddingAngle={2} strokeWidth={0}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e4e4e7", fontSize: 12 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </RePieChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}

export function ConfidenceBars({ values, title }: { values: number[]; title?: string }) {
  const buckets = React.useMemo(() => {
    const bins = [0, 0, 0, 0, 0];
    for (const v of values) {
      const c = Math.max(0, Math.min(1, v));
      bins[Math.min(4, Math.floor(c * 5))] += 1;
    }
    const labels = ["0–0.2", "0.2–0.4", "0.4–0.6", "0.6–0.8", "0.8–1.0"];
    return labels.map((name, i) => ({ name, count: bins[i] }));
  }, [values]);
  return (
    <ChartContainer title={title ?? "Confidence distribution"} description="Evidence confidence histogram">
      <ResponsiveContainer width="100%" height="100%">
        <ReBarChart data={buckets} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#71717a" }} tickLine={false} axisLine={{ stroke: "#e4e4e7" }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#71717a" }} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e4e4e7", fontSize: 12 }} />
          <Bar dataKey="count" name="Evidence" fill="#10b981" radius={[6, 6, 0, 0]} maxBarSize={44} />
        </ReBarChart>
      </ResponsiveContainer>
    </ChartContainer>
  );
}
