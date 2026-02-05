import React, { useState, useEffect, useMemo } from 'react'
import TodoForm from './components/TodoForm'
import TodoList from './components/TodoList'
import ThemeToggle from './components/ThemeToggle'
import StatsBar from './components/StatsBar'
import './App.css'

interface Todo {
  id: number
  text: string
  completed: boolean
}

function App() {
  const [todos, setTodos] = useState<Todo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  // Determine API base URL based on environment
  const getApiBase = () => {
    // In development (localhost:3000 or localhost:5173)
    if (window.location.hostname === 'localhost' && 
        (window.location.port === '3000' || window.location.port === '5173')) {
      return 'http://localhost:8000'
    }
    // In production (Docker)
    return '/api'
  }

  const API_BASE = getApiBase()

  // Sort todos: incomplete first, then completed
  const sortedTodos = useMemo(() => {
    return [...todos].sort((a, b) => {
      if (a.completed === b.completed) {
        return b.id - a.id // Most recent first within same completion status
      }
      return a.completed ? 1 : -1 // Incomplete first
    })
  }, [todos])

  // Calculate stats
  const stats = useMemo(() => {
    const total = todos.length
    const completed = todos.filter(todo => todo.completed).length
    const remaining = total - completed
    return { total, completed, remaining }
  }, [todos])

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark'
    if (savedTheme) {
      setTheme(savedTheme)
      document.documentElement.setAttribute('data-theme', savedTheme)
    }
    fetchTodos()
  }, [])

  const fetchTodos = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('Fetching from:', `${API_BASE}/todos`)
      const response = await fetch(`${API_BASE}/todos`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
      }
      
      const data = await response.json()
      setTodos(data)
    } catch (err) {
      console.error('Fetch error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch todos'
      setError(`Connection failed: ${errorMessage}. Please check if the backend service is running.`)
    } finally {
      setLoading(false)
    }
  }

  const addTodo = async (text: string) => {
    try {
      setError(null)
      const response = await fetch(`${API_BASE}/todos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
      }
      
      const newTodo = await response.json()
      setTodos(prev => [...prev, newTodo])
    } catch (err) {
      console.error('Add todo error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to add todo'
      setError(`Failed to add todo: ${errorMessage}`)
    }
  }

  const toggleTodo = async (id: number) => {
    try {
      setError(null)
      const todo = todos.find(t => t.id === id)
      if (!todo) return
      
      // Optimistically update UI
      setTodos(prev => prev.map(t => 
        t.id === id ? { ...t, completed: !t.completed } : t
      ))
      
      const response = await fetch(`${API_BASE}/todos/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed: !todo.completed })
      })
      
      if (!response.ok) {
        // Revert optimistic update on error
        setTodos(prev => prev.map(t => 
          t.id === id ? { ...t, completed: todo.completed } : t
        ))
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
      }
    } catch (err) {
      console.error('Toggle todo error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to update todo'
      setError(`Failed to update todo: ${errorMessage}`)
    }
  }

  const deleteTodo = async (id: number) => {
    try {
      setError(null)
      const todoToDelete = todos.find(t => t.id === id)
      
      // Optimistically update UI
      setTodos(prev => prev.filter(t => t.id !== id))
      
      const response = await fetch(`${API_BASE}/todos/${id}`, {
        method: 'DELETE'
      })
      
      if (!response.ok) {
        // Revert optimistic update on error
        if (todoToDelete) {
          setTodos(prev => [...prev, todoToDelete])
        }
        throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`)
      }
    } catch (err) {
      console.error('Delete todo error:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete todo'
      setError(`Failed to delete todo: ${errorMessage}`)
    }
  }

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    localStorage.setItem('theme', newTheme)
    document.documentElement.setAttribute('data-theme', newTheme)
  }

  const clearError = () => setError(null)

  const retryConnection = () => {
    fetchTodos()
  }

  if (loading) {
    return (
      <div className="loading">
        <div className="loading-spinner"></div>
        <span className="loading-text">Loading todos...</span>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Todo App</h1>
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </header>
      <main className="app-main">
        {error && (
          <div className="error-banner">
            <div className="error-content">
              <div className="error-message">{error}</div>
              <div className="error-actions">
                <button onClick={retryConnection} className="retry-button">Retry</button>
              </div>
            </div>
            <button onClick={clearError} className="error-close" aria-label="Close error">×</button>
          </div>
        )}
        <StatsBar stats={stats} />
        <TodoForm onAdd={addTodo} />
        <TodoList todos={sortedTodos} onToggle={toggleTodo} onDelete={deleteTodo} />
      </main>
    </div>
  )
}

export default App