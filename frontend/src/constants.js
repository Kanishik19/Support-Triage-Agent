export const URGENCY_META = {
  critical: { label: "Critical", color: "var(--danger)", bg: "var(--danger-soft)" },
  high: { label: "High", color: "var(--warning)", bg: "var(--warning-soft)" },
  medium: { label: "Medium", color: "var(--info)", bg: "var(--info-soft)" },
  low: { label: "Low", color: "var(--ink-soft)", bg: "var(--neutral-soft)" },
};

export const URGENCY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

export const CATEGORY_LABELS = {
  billing: "Billing",
  technical_issue: "Technical issue",
  account_access: "Account access",
  bug_report: "Bug report",
  feature_request: "Feature request",
  security: "Security",
  complaint: "Complaint",
  general_inquiry: "General inquiry",
};
