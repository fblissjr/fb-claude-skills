import { scoreColor } from "../utils/score-colors.js";

interface ScoreGaugeProps {
  label: string;
  score: number;
}

export function ScoreGauge({ label, score }: ScoreGaugeProps) {
  const color = scoreColor(score);
  const percent = Math.round(score * 100);

  return (
    <div className="score-gauge">
      <div className="score-gauge-header">
        <span className="score-gauge-label">{label}</span>
        <span className="score-gauge-value" style={{ color }}>
          {percent}%
        </span>
      </div>
      <div className="score-gauge-bar">
        <div
          className="score-gauge-fill"
          style={{ width: `${percent}%`, background: color }}
        />
      </div>
    </div>
  );
}
