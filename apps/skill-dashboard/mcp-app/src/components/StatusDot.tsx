interface Props {
  passed: boolean;
  title?: string;
}

export function StatusDot({ passed, title }: Props) {
  return (
    <span
      className={`status-dot ${passed ? "status-pass" : "status-fail"}`}
      title={title}
    />
  );
}
