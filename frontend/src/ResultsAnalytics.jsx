import React from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function ResultsAnalytics({ status }) {
  if (!status || !status.completed || !status.changes || Object.keys(status.changes).length === 0) {
    return null;
  }

  // Process data for visualizations
  const changes = status.changes;
  const addedItems = Object.entries(changes).filter(([k]) => k.startsWith('added_'));
  const removedItems = Object.entries(changes).filter(([k]) => k.startsWith('removed_'));
  
  const totalAdded = addedItems.reduce((sum, [, v]) => sum + v, 0);
  const totalRemoved = removedItems.reduce((sum, [, v]) => sum + v, 0);
  const totalChanges = totalAdded + totalRemoved;
  
  // Bar chart data - by category
  const categoryData = {};
  [...addedItems, ...removedItems].forEach(([key, value]) => {
    const category = key.replace('added_', '').replace('removed_', '').replace('_', ' ');
    if (!categoryData[category]) categoryData[category] = { name: category, added: 0, removed: 0 };
    if (key.startsWith('added_')) categoryData[category].added += value;
    else categoryData[category].removed += value;
  });
  const barData = Object.values(categoryData).sort((a, b) => (b.added + b.removed) - (a.added + a.removed));
  
  // Pie chart data
  const pieData = [
    { name: 'Added', value: totalAdded, color: '#00C853' },
    { name: 'Removed', value: totalRemoved, color: '#D32F2F' }
  ];
  
  // Top changes
  const topChanges = Object.entries(changes)
    .map(([key, value]) => ({
      name: key.replace('added_', 'New ').replace('removed_', 'Lost ').replace('_', ' '),
      value,
      type: key.startsWith('added_') ? 'added' : 'removed'
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);
  
  // Change severity assessment
  const changeSeverity = totalChanges > 50 ? 'HIGH' : totalChanges > 20 ? 'MODERATE' : 'LOW';
  const severityColor = changeSeverity === 'HIGH' ? '#D32F2F' : changeSeverity === 'MODERATE' ? '#FF9800' : '#4CAF50';

  return (
    <>
      <div className="divider" style={{margin: '4rem 0'}}/>
      <section className="section analytics-section">
        <h2 className="section-title">Comprehensive Analysis</h2>
        
        {/* Key Metrics */}
        <div className="metrics-grid">
          <div className="metric-card">
            <div className="metric-icon" style={{background: '#E8F5E9'}}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#00C853" strokeWidth="2">
                <path d="M12 5v14M5 12h14"/>
              </svg>
            </div>
            <div className="metric-content">
              <h3 className="metric-value">{totalAdded}</h3>
              <p className="metric-label">New Elements Added</p>
            </div>
          </div>
          
          <div className="metric-card">
            <div className="metric-icon" style={{background: '#FFEBEE'}}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#D32F2F" strokeWidth="2">
                <path d="M5 12h14"/>
              </svg>
            </div>
            <div className="metric-content">
              <h3 className="metric-value">{totalRemoved}</h3>
              <p className="metric-label">Elements Removed</p>
            </div>
          </div>
          
          <div className="metric-card">
            <div className="metric-icon" style={{background: '#F3E5F5'}}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#7B1FA2" strokeWidth="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
              </svg>
            </div>
            <div className="metric-content">
              <h3 className="metric-value">{totalChanges}</h3>
              <p className="metric-label">Total Changes</p>
            </div>
          </div>
          
          <div className="metric-card">
            <div className="metric-icon" style={{background: severityColor + '15'}}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke={severityColor} strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01"/>
              </svg>
            </div>
            <div className="metric-content">
              <h3 className="metric-value" style={{color: severityColor}}>{changeSeverity}</h3>
              <p className="metric-label">Change Severity</p>
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="charts-grid">
          {/* Bar Chart */}
          <div className="chart-card">
            <h3 className="chart-title">Changes by Category</h3>
            <p className="chart-subtitle">Added vs. Removed elements across detected categories</p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis dataKey="name" stroke="#666" style={{fontSize: '12px'}} />
                <YAxis stroke="#666" style={{fontSize: '12px'}} />
                <Tooltip contentStyle={{background: '#fff', border: '1px solid #e0e0e0', borderRadius: '4px'}} />
                <Legend wrapperStyle={{fontSize: '12px'}} />
                <Bar dataKey="added" fill="#00C853" name="Added" />
                <Bar dataKey="removed" fill="#D32F2F" name="Removed" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Pie Chart */}
          <div className="chart-card">
            <h3 className="chart-title">Change Distribution</h3>
            <p className="chart-subtitle">Overall breakdown of additions vs. removals</p>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Changes Table */}
        <div className="chart-card" style={{marginTop: '2rem'}}>
          <h3 className="chart-title">Top 10 Changes Detected</h3>
          <p className="chart-subtitle">Most significant changes identified during comparison</p>
          <div className="changes-table">
            <div className="table-header">
              <div className="table-cell">Change Type</div>
              <div className="table-cell">Count</div>
              <div className="table-cell">Status</div>
            </div>
            {topChanges.map((change, idx) => (
              <div key={idx} className="table-row">
                <div className="table-cell">{change.name}</div>
                <div className="table-cell">{change.value}</div>
                <div className="table-cell">
                  <span className={`status-badge ${change.type}`}>
                    {change.type === 'added' ? 'NEW' : 'REMOVED'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Insights */}
        <div className="insights-grid">
          <div className="insight-card">
            <h4 className="insight-title">🎯 Key Findings</h4>
            <ul className="insight-list">
              {totalAdded > totalRemoved && <li>More infrastructure added than removed — indicating development</li>}
              {totalRemoved > totalAdded && <li>More elements removed than added — potential degradation detected</li>}
              {totalAdded === totalRemoved && <li>Balanced changes detected — equal additions and removals</li>}
              {barData[0] && <li>Most impacted category: <strong>{barData[0].name}</strong> with {barData[0].added + barData[0].removed} changes</li>}
              {changeSeverity === 'HIGH' && <li>High change volume requires immediate attention and review</li>}
              {changeSeverity === 'LOW' && <li>Minimal changes detected — infrastructure appears stable</li>}
            </ul>
          </div>

          <div className="insight-card">
            <h4 className="insight-title">💡 Recommendations</h4>
            <ul className="insight-list">
              {totalRemoved > 5 && <li>Schedule site inspection to verify removed infrastructure</li>}
              {totalAdded > 10 && <li>Document new additions for maintenance records</li>}
              {barData.some(d => d.name.includes('pothole')) && <li>Pothole changes detected — prioritize road maintenance</li>}
              {barData.some(d => d.name.includes('sign') || d.name.includes('traffic')) && <li>Traffic infrastructure changes — update navigation systems</li>}
              <li>Download full report for detailed frame-by-frame analysis</li>
              <li>Compare with historical data to identify trends</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
