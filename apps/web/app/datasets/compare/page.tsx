"use client";

import * as React from "react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { GitCompareArrows } from "lucide-react";
import { clientFetch, API_BASE_URL, apiUrl } from "@/lib/api";
import { Button } from "@/app/components/ui/button";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/app/components/ui/card";
import { Select } from "@/app/components/ui/input";
import { Badge } from "@/app/components/ui/badge";
import { PageHeader } from "@/app/components/data/PageHeader";
import { StatCard } from "@/app/components/data/StatCard";
import { EmptyState, ErrorState, CardsSkeleton } from "@/app/components/data/States";

type DsItem = { id: string; filename: string };
type Detail = {
  id: string;
  filename: string;
  format: string;
  rows: number | null;
  cols: number | null;
  sha256: string | null;
  size_bytes: number | null;
  profile: {
    rows: number;
    columns: number;
    column_profiles: { name: string; dtype: string; kind: string; null_count: number; unique_count: number | null }[];
    duplicate_rows: number;
    missing_ratio: number;
  } | null;
};

function CompareColumn({ label, a, b, higherBetter }: { label: string; a: string; b: string; higherBetter?: boolean }) {
  const num = (v: string) => {
    const n = parseFloat(v.replace(/[^0-9.\-]/g, ""));
    return Number.isNaN(n) ? null : n;
  };
  const an = num(a);
  const bn = num(b);
  const win: 0 | 1 | 2 =
    an == null || bn == null || an === bn ? 0 : higherBetter === false ? (an < bn ? 1 : 2) : an > bn ? 1 : 2;
  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 rounded-lg border border-zinc-100 px-3 py-2 text-sm">
      <span className={`truncate text-right tabular-nums ${win === 1 ? "font-semibold text-emerald-700" : ""}`} title={a}>{a}</span>
      <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">{label}</span>
      <span className={`truncate tabular-nums ${win === 2 ? "font-semibold text-emerald-700" : ""}`} title={b}>{b}</span>
    </div>
  );
}

export default function ComparePage() {
  const locale = useLocale();
  const [items, setItems] = useState<DsItem[]>([]);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [left, setLeft] = useState<Detail | null>(null);
  const [right, setRight] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    clientFetch("/api/v1/datasets/")
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<{ datasets: DsItem[] }>;
      })
      .then((d) => {
        setItems(d.datasets);
        if (d.datasets.length >= 2) {
          setLeftId(d.datasets[0].id);
          setRightId(d.datasets[1].id);
        } else if (d.datasets.length === 1) {
          setLeftId(d.datasets[0].id);
        }
      })
      .catch((e) => setErr(`${t(locale, "common.apiUnreachable").replace("{url}", API_BASE_URL)} ${String(e)}`))
      .finally(() => setLoadingList(false));
  }, []);

  useEffect(() => {
    if (!leftId && !rightId) return;
    let cancelled = false;
    setLoadingDetail(true);
    Promise.all(
      [leftId, rightId].map((id) =>
        id ? clientFetch(`/api/v1/datasets/${id}`).then((r) => (r.ok ? (r.json() as Promise<Detail>) : null)) : Promise.resolve(null)
      )
    )
      .then(([l, r]) => {
        if (!cancelled) {
          setLeft(l);
          setRight(r);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoadingDetail(false);
      });
    return () => {
      cancelled = true;
    };
  }, [leftId, rightId]);

  const leftCols = left?.profile?.column_profiles ?? [];
  const rightCols = right?.profile?.column_profiles ?? [];
  const rightNames = new Set(rightCols.map((c) => c.name.toLowerCase()));
  const common = leftCols.filter((c) => rightNames.has(c.name.toLowerCase()));
  const onlyLeft = leftCols.filter((c) => !rightNames.has(c.name.toLowerCase()));
  const leftNames = new Set(leftCols.map((c) => c.name.toLowerCase()));
  const onlyRight = rightCols.filter((c) => !leftNames.has(c.name.toLowerCase()));

  const picker = (value: string, onChange: (v: string) => void, label: string) => (
    <div className="min-w-0 flex-1">
      <label className="sr-only">{label}</label>
      <Select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        <option value="">{t(locale, "cmpds.selectPlaceholder")}</option>
        {items.map((d) => (
          <option key={d.id} value={d.id}>{d.filename}</option>
        ))}
      </Select>
    </div>
  );

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow={t(locale, "cmpds.eyebrow")}
        title={t(locale, "nav.compareDatasets")}
        description={t(locale, "cmpds.subtitle")}
        actions={
          <Link href="/datasets"><Button variant="secondary" size="sm">{t(locale, "dsd.back")}</Button></Link>
        }
      />
      {err && <ErrorState message={err} />}
      {loadingList ? (
        <CardsSkeleton count={2} />
      ) : items.length < 2 ? (
        <EmptyState
          icon={<GitCompareArrows className="size-5 text-zinc-400" aria-hidden />}
          title={t(locale, "cmpds.needTwoTitle")}
          description={t(locale, "cmpds.uploadTwo")}
          action={<Link href="/datasets"><Button size="sm">{t(locale, "cmpds.uploadCta")}</Button></Link>}
        />
      ) : (
        <>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            {picker(leftId, setLeftId, t(locale, "cmpds.left"))}
            <span aria-hidden className="text-center text-sm font-semibold text-zinc-400">vs</span>
            {picker(rightId, setRightId, t(locale, "cmpds.right"))}
          </div>
          {loadingDetail ? (
            <CardsSkeleton count={2} />
          ) : left && right ? (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                {[left, right].map((d, i) => (
                  <Card key={d.id} className="min-w-0">
                    <CardHeader>
                      <CardTitle className="truncate text-sm" title={d.filename}>{i === 0 ? "A · " : "B · "}{d.filename}</CardTitle>
                      <CardDescription className="font-mono text-[11px]">sha256 {d.sha256?.slice(0, 12) ?? "—"}…</CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-2 gap-2">
                      <StatCard label={t(locale, "dsd.rows")} value={String(d.rows ?? "—")} />
                      <StatCard label={t(locale, "dsd.columns")} value={String(d.cols ?? "—")} />
                    </CardContent>
                  </Card>
                ))}
              </div>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">{t(locale, "cmpds.headToHead")}</CardTitle>
                  <CardDescription className="text-xs">{t(locale, "cmpds.emeraldNote")}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <CompareColumn label={t(locale, "cmpds.unitRows")} a={String(left.rows ?? "—")} b={String(right.rows ?? "—")} />
                  <CompareColumn label={t(locale, "cmpds.unitColumns")} a={String(left.cols ?? "—")} b={String(right.cols ?? "—")} />
                  <CompareColumn
                    label={t(locale, "cmpds.unitMissing")}
                    a={left.profile ? `${(left.profile.missing_ratio * 100).toFixed(1)}%` : "—"}
                    b={right.profile ? `${(right.profile.missing_ratio * 100).toFixed(1)}%` : "—"}
                    higherBetter={false}
                  />
                  <CompareColumn label={t(locale, "cmpds.unitDuplicates")} a={String(left.profile?.duplicate_rows ?? "—")} b={String(right.profile?.duplicate_rows ?? "—")} higherBetter={false} />
                  <CompareColumn
                    label={t(locale, "cmpds.unitSize")}
                    a={left.size_bytes != null ? `${(left.size_bytes / 1024).toFixed(1)} KB` : "—"}
                    b={right.size_bytes != null ? `${(right.size_bytes / 1024).toFixed(1)} KB` : "—"}
                  />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">{t(locale, "cmpds.overlapTitle")}</CardTitle>
                            <CardDescription className="text-xs">
            {t(locale, "cmpds.sharedLine")
              .replace("{shared}", String(common.length))
              .replace("{left}", String(onlyLeft.length))
              .replace("{right}", String(onlyRight.length))}
          </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-1.5">
                  {common.map((c) => <Badge key={c.name} variant="success">{c.name}</Badge>)}
                  {onlyLeft.map((c) => <Badge key={c.name} variant="secondary">A: {c.name}</Badge>)}
                  {onlyRight.map((c) => <Badge key={c.name} variant="outline">B: {c.name}</Badge>)}
                  {common.length + onlyLeft.length + onlyRight.length === 0 && (
                    <p className="text-xs text-zinc-500">{t(locale, "cmpds.noProfiles")}</p>
                  )}
                </CardContent>
              </Card>
            </>
          ) : (
            <EmptyState title={t(locale, "cmpds.selectTwo")} description={t(locale, "cmpds.pickOneEach")} />
          )}
        </>
      )}
    </div>
  );
}
