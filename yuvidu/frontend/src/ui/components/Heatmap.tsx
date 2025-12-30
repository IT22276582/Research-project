import React from "react";
import { scaleLinear } from "d3-scale";
import "./Heatmap.css";

interface HeatmapProps {
  percentages: {
    morning: number;
    afternoon: number;
    evening: number;
    night: number;
  };
}

const Heatmap: React.FC<HeatmapProps> = ({ percentages }) => {
  // Create hourly data for better heatmap visualization
  const hours = [
    "6AM", "7AM", "8AM", "9AM", "10AM", "11AM",
    "12PM", "1PM", "2PM", "3PM", "4PM", "5PM",
    "6PM", "7PM", "8PM", "9PM", "10PM", "11PM",
    "12AM", "1AM", "2AM", "3AM", "4AM", "5AM"
  ];

  // Map percentages to hourly values (distribute across time periods)
  const hourlyData = hours.map((hour, index) => {
    let value;
    if (index < 6) { // Morning (6AM-11AM)
      value = percentages?.morning ?? 0;
    } else if (index < 12) { // Afternoon (12PM-5PM)
      value = percentages?.afternoon ?? 0;
    } else if (index < 18) { // Evening (6PM-11PM)
      value = percentages?.evening ?? 0;
    } else { // Night (12AM-5AM)
      value = percentages?.night ?? 0;
    }
    return { hour, value };
  });

  // Better heatmap color scale - more distinct colors for intensity
  const colorScale = scaleLinear<string>()
    .domain([0, 20, 40, 60, 80, 100])
    .range([
      "#dc2626", // Dark red for very low
      "#f87171", // Light red for low  
      "#fbbf24", // Amber for medium-low
      "#facc15", // Yellow for medium
      "#84cc16", // Lime for medium-high
      "#16a34a"  // Green for high
    ]);

  return (
    <div className="heatmap-container">
      <h3 className="heatmap-title">
        🌡️ Prediction Intensity Heatmap
      </h3>

      {/* Traditional heatmap grid */}
      <div className="heatmap-grid-section">
        {/* Time period labels */}
        <div className="heatmap-period-labels">
          <div></div>
          <div className="heatmap-period-label" style={{ gridColumn: "2/8" }}>Morning</div>
          <div className="heatmap-period-label" style={{ gridColumn: "8/14" }}>Afternoon</div>
          <div className="heatmap-period-label" style={{ gridColumn: "14/20" }}>Evening</div>
          <div className="heatmap-period-label" style={{ gridColumn: "20/26" }}>Night</div>
        </div>

        {/* Hour labels */}
        <div className="heatmap-hour-labels">
          <div>Time</div>
          {hours.map(hour => (
            <div key={hour} className="heatmap-hour-label">{hour}</div>
          ))}
        </div>

        {/* Heatmap cells */}
        <div className="heatmap-cells">
          <div className="heatmap-intensity-label">Intensity</div>
          {hourlyData.map((data, index) => {
            const color = colorScale(data.value);
            // Better text contrast based on background color
            const textColor = data.value >= 60 ? "heatmap-text-light" : data.value >= 40 ? "heatmap-text-medium" : "heatmap-text-dark";
            
            return (
              <div
                key={index}
                className="heatmap-cell"
                style={{ background: color }}
                title={`${data.hour}: ${data.value.toFixed(1)}% intensity`}
              >
                <div className="heatmap-cell-content">
                  <div className="heatmap-cell-hour">
                    {data.hour}
                  </div>
                  <div className={`heatmap-cell-percentage ${textColor}`}>
                    {data.value.toFixed(0)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary statistics */}
      <div className="heatmap-summary">
        <div className="heatmap-summary-card heatmap-summary-morning">
          <div className="heatmap-summary-label">Morning</div>
          <div className="heatmap-summary-value">
            {(percentages?.morning ?? 0).toFixed(1)}%
          </div>
        </div>
        <div className="heatmap-summary-card heatmap-summary-afternoon">
          <div className="heatmap-summary-label">Afternoon</div>
          <div className="heatmap-summary-value">
            {(percentages?.afternoon ?? 0).toFixed(1)}%
          </div>
        </div>
        <div className="heatmap-summary-card heatmap-summary-evening">
          <div className="heatmap-summary-label">Evening</div>
          <div className="heatmap-summary-value">
            {(percentages?.evening ?? 0).toFixed(1)}%
          </div>
        </div>
        <div className="heatmap-summary-card heatmap-summary-evening">
          <div className="heatmap-summary-label">Night</div>
          <div className="heatmap-summary-value">
            {(percentages?.night ?? 0).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Color scale legend */}
      <div className="heatmap-legend">
        <div className="heatmap-legend-title">
          Intensity Scale (Low → High)
        </div>
        <div className="heatmap-legend-container">
          <span className="heatmap-legend-label">0%</span>
          <div className="heatmap-legend-bar">
            {[0, 20, 40, 60, 80, 100].map((val, idx) => {
              const textColor = val >= 60 ? "heatmap-legend-segment-light-text" : "heatmap-legend-segment-dark-text";
              return (
                <div
                  key={idx}
                  className={`heatmap-legend-segment ${textColor}`}
                  style={{ background: colorScale(val) }}
                >
                  {val}%
                </div>
              );
            })}
          </div>
          <span className="heatmap-legend-label">100%</span>
        </div>
        <div className="heatmap-legend-scale">
          <span className="heatmap-legend-scale-label">Very Low</span>
          <span className="heatmap-legend-scale-label">Low</span>
          <span className="heatmap-legend-scale-label">Medium</span>
          <span className="heatmap-legend-scale-label">High</span>
          <span className="heatmap-legend-scale-label">Very High</span>
        </div>
      </div>
    </div>
  );
};

export default Heatmap;
