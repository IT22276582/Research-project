import styles from "./Sparkline.module.css";

type SparklineProps = {
  points: { x: number; y: number }[];
  width?: number;
  height?: number;
  color?: string;
  label: string;
  value: string;
  className?: string;
};

export function Sparkline({
  points,
  width,
  height,
  color = "#22d3ee",
  label,
  value,
  className = "",
}: SparklineProps) {
  if (!points.length) {
    return (
      <div className={styles.sparkline}>
        <div className={styles.header}>
          <span className={styles.label}>{label}</span>
          <span className={styles.value}>{value}</span>
        </div>
        <div className={styles.empty}>Waiting for data...</div>
      </div>
    );
  }

  const minY = Math.min(...points.map((p) => p.y));
  const maxY = Math.max(...points.map((p) => p.y));
  const spanY = Math.max(1e-6, maxY - minY);
  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  const spanX = Math.max(1, maxX - minX);

  const gradientId = `grad-${label.replace(/\s+/g, "-")}`;

  // Use default dimensions if not provided for calculations
  const calcWidth = width ?? 480;
  const calcHeight = height ?? 200;
  
  const path = points
    .map((p, idx) => {
      const x = ((p.x - minX) / spanX) * (calcWidth - 20) + 10;
      const y = calcHeight - (((p.y - minY) / spanY) * (calcHeight - 20) + 10);
      return `${idx === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");

  // Use responsive dimensions if not explicitly provided
  const svgWidth = width ?? "100%";
  const svgHeight = height ?? calcHeight;
  
  return (
    <div className={`${styles.sparkline} ${className}`}>
      <div className={styles.header}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>{value}</span>
      </div>
      <svg
        width={svgWidth}
        height={svgHeight}
        role="presentation"
        style={{
          width: svgWidth,
          height: svgHeight,
          minWidth: "220px",
          minHeight: "140px"
        }}
        viewBox={`0 0 ${calcWidth} ${calcHeight}`}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={path} stroke={color} strokeWidth={2} fill="none" />
        <path
          d={`${path} L ${calcWidth - 10} ${calcHeight - 10} L 10 ${calcHeight - 10} Z`}
          fill={`url(#${gradientId})`}
          opacity={0.6}
        />
      </svg>
    </div>
  );
}
