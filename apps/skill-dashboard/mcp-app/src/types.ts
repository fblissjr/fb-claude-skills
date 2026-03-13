// Domain types for the skill dashboard

export interface CheckResult {
  name: string;
  passed: boolean;
  detail: string;
}

export interface SkillResult {
  name: string;
  checks: {
    specCompliance: CheckResult;
    tokenBudget: CheckResult;
    bodySize: CheckResult;
    staleness: CheckResult;
    descriptionQuality: CheckResult;
  };
}

export interface PluginResult {
  name: string;
  checks: {
    manifestFields: CheckResult;
    marketplaceListing: CheckResult;
    readmeExists: CheckResult;
  };
}

export interface RepoCheckResult {
  check: string;
  passed: boolean;
  detail: string;
}

export interface QualitySummary {
  passed: number;
  failed: number;
  total: number;
}

export interface QualityMeta {
  generatedAt: string;
  budgetWarn: number;
  budgetCritical: number;
}

export interface QualityCheckContent {
  type: "quality-check";
  skills: SkillResult[];
  plugins: PluginResult[];
  repo: RepoCheckResult[];
  summary: QualitySummary;
  meta: QualityMeta;
}

export type StructuredContent = QualityCheckContent;
