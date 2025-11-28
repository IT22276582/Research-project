import React from 'react';
import { startOfWeek, addDays, isSameDay } from 'date-fns';
import { scaleLinear } from 'd3-scale';

interface HeatmapProps {
  data: { date: Date; value: number }[];
  fromDate: Date;
  toDate: Date;
}

interface WeekData {
  name: string;
  days: (number | null)[];
  dates: Date[];
}

const Heatmap: React.FC<HeatmapProps> = ({ data, fromDate, toDate }) => {
  // Generate all days in the date range
  const daysInRange: Date[] = [];
  let currentDate = new Date(fromDate);
  
  while (currentDate <= toDate) {
    daysInRange.push(new Date(currentDate));
    currentDate = addDays(currentDate, 1);
  }

  // Group data by week
  const weeks: { [key: string]: { date: Date; value: number | null }[] } = {};
  
  daysInRange.forEach((day) => {
    const weekStart = startOfWeek(day, { weekStartsOn: 0 });
    const weekKey = weekStart.toISOString();
    
    if (!weeks[weekKey]) {
      weeks[weekKey] = Array(7).fill(null).map((_, i) => ({
        date: addDays(weekStart, i),
        value: null,
      }));
    }
    
    const dayData = data.find(d => isSameDay(d.date, day));
    const dayIndex = weeks[weekKey].findIndex(d => isSameDay(d.date, day));
    
    if (dayIndex !== -1 && dayData) {
      weeks[weekKey][dayIndex].value = dayData.value;
    }
  });

  // Prepare data for the heatmap
  const heatmapData: WeekData[] = Object.entries(weeks).map(([_, weekDays], weekIndex) => ({
    name: `Week ${weekIndex + 1}`,
    days: weekDays.map(day => day.value),
    dates: weekDays.map(day => day.date)
  }));

  // Color scale for the heatmap
  const colorScale = scaleLinear<string>()
    .domain([0, 0.5, 1])
    .range(['#e0f7fa', '#00bcd4', '#006064']);

  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  // Function to safely format the value
  const formatValue = (value: number | null): string => {
    if (value === null || typeof value !== 'number' || isNaN(value)) return '';
    return value > 0 ? value.toFixed(1) : '';
  };

  return (
    <div style={{ 
      width: '100%', 
      marginTop: '2rem',
      minHeight: '300px' // Ensure minimum height
    }}>
      <h3>Weekly Productivity Heatmap</h3>
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '8px',
        backgroundColor: '#f9f9f9',
        padding: '1rem',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          gap: '4px', 
          marginBottom: '8px' 
        }}>
          {days.map((day, i) => (
            <div 
              key={i} 
              style={{ 
                width: '24px', 
                textAlign: 'center', 
                fontSize: '12px',
                fontWeight: 'bold'
              }}
            >
              {day[0]}
            </div>
          ))}
        </div>
        
        {heatmapData.map((week, weekIndex) => (
          <div 
            key={weekIndex} 
            style={{ 
              display: 'flex', 
              justifyContent: 'center', 
              gap: '4px' 
            }}
          >
            {week.days.map((value, dayIndex) => {
              const color = value !== null ? colorScale(value) : '#f0f0f0';
              
              return (
                <div
                  key={dayIndex}
                  style={{
                    width: '24px',
                    height: '24px',
                    backgroundColor: color,
                    borderRadius: '4px',
                    cursor: 'pointer',
                    position: 'relative',
                    border: '1px solid #e0e0e0'
                  }}
                  title={
                    value !== null 
                      ? `Value: ${value}\nDate: ${week.dates[dayIndex].toLocaleDateString()}` 
                      : 'No data'
                  }
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: value !== null ? (value > 0.5 ? 'white' : 'rgba(0, 0, 0, 0.87)') : 'transparent',
                      fontSize: '10px',
                      fontWeight: 'bold'
                    }}
                  >
                    {formatValue(value)}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginTop: '16px',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span style={{ fontSize: '12px', color: '#666' }}>Less Productive</span>
        {[0, 0.25, 0.5, 0.75, 1].map((value) => (
          <div
            key={value}
            style={{
              width: '20px',
              height: '20px',
              backgroundColor: colorScale(value),
              borderRadius: '4px',
              border: '1px solid #e0e0e0'
            }}
          />
        ))}
        <span style={{ fontSize: '12px', color: '#666' }}>More Productive</span>
      </div>
    </div>
  );
};

export default Heatmap;