import React from 'react'

interface StatsBarProps {
  stats: {
    total: number
    completed: number
    remaining: number
  }
}

function StatsBar({ stats }: StatsBarProps) {
  return (
    <div className="stats-bar">
      <div className="stats-item">
        <span className="stats-number">{stats.total}</span>
        <span className="stats-label">Total</span>
      </div>
      <div className="stats-item">
        <span className="stats-number">{stats.remaining}</span>
        <span className="stats-label">Remaining</span>
      </div>
      <div className="stats-item">
        <span className="stats-number">{stats.completed}</span>
        <span className="stats-label">Completed</span>
      </div>
    </div>
  )
}

export default StatsBar