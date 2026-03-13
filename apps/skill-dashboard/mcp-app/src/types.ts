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

export interface FileTokenEntry {
  path: string;
  chars: number;
  tokens: number;
  pctOfTotal: number;
}

export interface SkillMeasureContent {
  type: "skill-measure";
  skillName: string;
  skillDir: string;
  files: FileTokenEntry[];
  totalTokens: number;
  budget: { warn: number; critical: number };
}

export interface SkillVerifyContent {
  type: "skill-verify";
  skillName: string;
  previousDate: string | null;
  newDate: string;
  path: string;
}

export type StructuredContent =
  | QualityCheckContent
  | SkillMeasureContent
  | SkillVerifyContent;
