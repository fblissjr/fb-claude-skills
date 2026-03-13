import type { QualityMeta, SkillResult } from "../types.js";
import { StatusDot } from "./StatusDot.js";
import { TokenBudgetBar } from "./TokenBudgetBar.js";

interface Props {
  skills: SkillResult[];
  meta: QualityMeta;
  selectedSkill?: string | null;
  onSelect?: (skillName: string) => void;
}

export function SkillTable({ skills, meta, selectedSkill, onSelect }: Props) {
  return (
    <div className="table-wrapper">
      <table className="check-table">
        <thead>
          <tr>
            <th>Skill</th>
            <th>Spec</th>
            <th>Description</th>
            <th>Fresh</th>
            <th>Body</th>
            <th>Tokens</th>
          </tr>
        </thead>
        <tbody>
          {skills.map((skill) => {
            const isSelected = selectedSkill === skill.name;
            const className = [
              onSelect ? "clickable" : "",
              isSelected ? "selected" : "",
            ]
              .filter(Boolean)
              .join(" ");

            return (
              <tr
                key={skill.name}
                className={className}
                onClick={onSelect ? () => onSelect(skill.name) : undefined}
              >
                <td className="cell-name">{skill.name}</td>
                <td className="cell-status">
                  <StatusDot
                    passed={skill.checks.specCompliance.passed}
                    title={skill.checks.specCompliance.detail}
                  />
                </td>
                <td className="cell-status">
                  <StatusDot
                    passed={skill.checks.descriptionQuality.passed}
                    title={skill.checks.descriptionQuality.detail}
                  />
                </td>
                <td className="cell-status">
                  <StatusDot
                    passed={skill.checks.staleness.passed}
                    title={skill.checks.staleness.detail}
                  />
                </td>
                <td className="cell-status">
                  <StatusDot
                    passed={skill.checks.bodySize.passed}
                    title={skill.checks.bodySize.detail}
                  />
                </td>
                <td className="cell-budget">
                  <TokenBudgetBar
                    detail={skill.checks.tokenBudget.detail}
                    passed={skill.checks.tokenBudget.passed}
                    budgetWarn={meta.budgetWarn}
                    budgetCritical={meta.budgetCritical}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
