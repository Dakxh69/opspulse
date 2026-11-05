/**
 * OpsPulse Frontend — Type Definitions
 * Matches backend OpenAPI models and schemas.
 */

export type UserRole = 'ADMIN' | 'OPERATOR' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type AgentStatus = 'ONLINE' | 'DEGRADED' | 'OFFLINE';

export interface Agent {
  id: string;
  name: string;
  hostname: string;
  os_type: string;
  agent_version: string;
  status: AgentStatus;
  last_heartbeat: string | null;
  created_at: string;
  revoked_at: string | null;
}

export type AlertSeverity = 'WARNING' | 'CRITICAL';
export type AlertOperator = '>' | '>=' | '<' | '<=' | '==';
export type DimensionAggregation = 'EACH' | 'MAX';

export interface AlertRule {
  id: string;
  name: string;
  metric_key: string;
  operator: AlertOperator;
  threshold: number;
  severity: AlertSeverity;
  evaluation_window_seconds: number;
  consecutive_breaches: number;
  cooldown_seconds: number;
  dimension_filter: string | null;
  dimension_aggregation: DimensionAggregation | null;
  agent_id: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type IncidentStatus = 'OPEN' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';
export type IncidentEventType =
  | 'DETECTED'
  | 'ACKNOWLEDGED'
  | 'INVESTIGATING'
  | 'NOTE_ADDED'
  | 'RESOLVED'
  | 'REOPENED'
  | 'CLOSED'
  | 'AUTO_CLEARED';

export interface IncidentEvent {
  id: string;
  incident_id: string;
  event_type: IncidentEventType;
  message: string;
  actor_user_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Incident {
  id: string;
  agent_id: string;
  rule_id: string | null;
  dimension: string | null;
  title: string;
  description: string;
  severity: AlertSeverity;
  status: IncidentStatus;
  first_detected_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  acknowledged_by_user_id: string | null;
  resolved_by_user_id: string | null;
  events?: IncidentEvent[];
}

export interface MetricSample {
  timestamp: string;
  cpu_usage_percent: number;
  memory_usage_percent: number;
  disks?: Array<{
    mount_point: string;
    usage_percent: number;
    used_bytes: number;
    total_bytes: number;
  }>;
  networks?: Array<{
    interface_name: string;
    bytes_sent_per_sec: number;
    bytes_recv_per_sec: number;
  }>;
}

