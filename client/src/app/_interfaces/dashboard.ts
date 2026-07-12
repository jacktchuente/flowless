export interface DashboardStats {
  channels_total: number;
  channels_enabled: number;
  channels_on_air: number;
  open_alerts: number;
  channels_with_alerts: number;
  sources_total: number;
  sources_stale: number;
  last_generation_at: string | null;
}
export interface DashboardAlert {
  severity: "error" | "warning";
  kind: string;
  object_type: "tv_channel" | "media_source";
  object_id: number;
  object_name: string;
  message: string;
  occurred_at: string;
}
export interface DashboardActivity {
  kind: string;
  status: "success" | "error" | "info";
  label_params: Record<string, unknown>;
  occurred_at: string;
  tv_channel_id: number | null;
}
export interface DashboardOnAir {
  tv_channel_id: number;
  name: string;
  logo: string | null;
  current: { title: string; starts_at: string; ends_at: string };
  next: { title: string; starts_at: string } | null;
}
export interface DashboardOverview {
  stats: DashboardStats;
  alerts: DashboardAlert[];
  recent_activity: DashboardActivity[];
  on_air: DashboardOnAir[];
}
