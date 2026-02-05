import React from 'react'

interface Todo {
  id: number
  text: string
  completed: boolean
}

interface TodoItemProps {
  todo: Todo
  onToggle: (id: number) => void
  onDelete: (id: number) => void
}

function TodoItem({ todo, onToggle, onDelete }: TodoItemProps) {
  const handleToggle = () => {
    onToggle(todo.id)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete(todo.id)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      handleToggle()
    }
  }

  return (
    <div 
      className={`todo-item ${todo.completed ? 'completed' : ''}`}
      onClick={handleToggle}
      onKeyDown={handleKeyDown}
      tabIndex={0}
      role="button"
      aria-label={`Mark todo "${todo.text}" as ${todo.completed ? 'incomplete' : 'complete'}`}
    >
      <input
        type="checkbox"
        checked={todo.completed}
        onChange={handleToggle}
        className="todo-checkbox"
        tabIndex={-1}
        aria-label={`Todo: ${todo.text}`}
      />
      <span className="todo-text">{todo.text}</span>
      <button
        onClick={handleDelete}
        className="delete-button"
        aria-label={`Delete todo: ${todo.text}`}
        tabIndex={0}
      >
        ×
      </button>
    </div>
  )
}

export default TodoItem