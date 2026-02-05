import React, { useState } from 'react'

interface TodoFormProps {
  onAdd: (text: string) => Promise<void>
}

function TodoForm({ onAdd }: TodoFormProps) {
  const [text, setText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!text.trim() || isSubmitting) return

    setIsSubmitting(true)
    try {
      await onAdd(text.trim())
      setText('')
    } catch (error) {
      console.error('Error adding todo:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e as any)
    }
  }

  return (
    <form className="todo-form" onSubmit={handleSubmit}>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What needs to be done?"
        disabled={isSubmitting}
        className="todo-input"
        maxLength={500}
        aria-label="New todo text"
      />
      <button 
        type="submit" 
        disabled={!text.trim() || isSubmitting}
        className="add-button"
        aria-label="Add new todo"
      >
        {isSubmitting ? 'Adding...' : 'Add Todo'}
      </button>
    </form>
  )
}

export default TodoForm