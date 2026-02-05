from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database setup with better error handling
def init_database(max_retries=10, delay=2):
    """Initialize database with retry logic"""
    for attempt in range(max_retries):
        try:
            DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://todouser:todopass@db:5432/todoapp")
            logger.info(f"Attempt {attempt + 1}: Using database URL: {DATABASE_URL}")
            
            # Create engine with proper PostgreSQL configuration
            engine = create_engine(
                DATABASE_URL,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=300,
                pool_size=10,
                max_overflow=20,
                connect_args={
                    "connect_timeout": 30
                }
            )
            
            # Test connection using text() for raw SQL
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Database engine created successfully")
            return engine
            
        except Exception as e:
            logger.error(f"Database setup attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay = min(delay * 1.5, 30)  # Exponential backoff with cap
            else:
                logger.error("All database setup attempts failed")
                raise
    
    raise Exception("Failed to initialize database after all retries")

try:
    engine = init_database()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
except Exception as e:
    logger.error(f"Critical database setup error: {e}")
    raise

# Database model
class TodoDB(Base):
    __tablename__ = "todos"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(500), nullable=False)
    completed = Column(Boolean, default=False, nullable=False)

# Create tables with error handling and retry logic
def create_tables(max_retries=5):
    """Create database tables with retry logic"""
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            return
        except Exception as e:
            logger.error(f"Table creation attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise

create_tables()

# Pydantic models
class TodoCreate(BaseModel):
    text: str

class TodoUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None

class Todo(BaseModel):
    id: int
    text: str
    completed: bool
    
    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI(
    title="Todo API", 
    version="1.0.0",
    description="A simple Todo API built with FastAPI and PostgreSQL"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # Local development
        "http://localhost:5173",     # Vite dev server
        "http://localhost",          # Docker frontend (port 80)
        "http://localhost:80",       # Docker frontend explicit port
        "http://frontend",           # Docker service name
        "http://frontend:80",        # Docker service with port
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Dependency to get DB session with better error handling and retry logic
def get_db():
    """Get database session with retry logic"""
    max_retries = 3
    for attempt in range(max_retries):
        db = None
        try:
            db = SessionLocal()
            # Test the connection using text() for raw SQL
            db.execute(text("SELECT 1"))
            yield db
            break
        except Exception as e:
            logger.error(f"Database session attempt {attempt + 1} failed: {e}")
            if db:
                db.rollback()
                db.close()
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                raise HTTPException(
                    status_code=503, 
                    detail="Database connection failed after multiple retries"
                )
        finally:
            if db:
                db.close()

# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    try:
        # Test database connection using text() for raw SQL
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "message": "Todo API is running",
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return await root()

# API endpoints
@app.get("/todos", response_model=List[Todo], tags=["Todos"])
async def get_todos(db: Session = Depends(get_db)):
    """Get all todos"""
    try:
        logger.info("Fetching all todos")
        todos = db.query(TodoDB).all()
        logger.info(f"Found {len(todos)} todos")
        return todos
    except Exception as e:
        logger.error(f"Error fetching todos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch todos: {str(e)}")

@app.post("/todos", response_model=Todo, tags=["Todos"])
async def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    """Create a new todo"""
    try:
        logger.info(f"Creating todo: {todo.text}")
        
        if not todo.text or not todo.text.strip():
            raise HTTPException(status_code=400, detail="Todo text cannot be empty")
        
        if len(todo.text.strip()) > 500:
            raise HTTPException(status_code=400, detail="Todo text cannot exceed 500 characters")
        
        db_todo = TodoDB(text=todo.text.strip(), completed=False)
        db.add(db_todo)
        db.commit()
        db.refresh(db_todo)
        
        logger.info(f"Created todo with ID: {db_todo.id}")
        return db_todo
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create todo: {str(e)}")

@app.get("/todos/{todo_id}", response_model=Todo, tags=["Todos"])
async def get_todo(todo_id: int, db: Session = Depends(get_db)):
    """Get a specific todo by ID"""
    try:
        logger.info(f"Fetching todo with ID: {todo_id}")
        todo = db.query(TodoDB).filter(TodoDB.id == todo_id).first()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch todo: {str(e)}")

@app.put("/todos/{todo_id}", response_model=Todo, tags=["Todos"])
async def update_todo(todo_id: int, todo_update: TodoUpdate, db: Session = Depends(get_db)):
    """Update a todo"""
    try:
        logger.info(f"Updating todo with ID: {todo_id}")
        todo = db.query(TodoDB).filter(TodoDB.id == todo_id).first()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        if todo_update.text is not None:
            if not todo_update.text.strip():
                raise HTTPException(status_code=400, detail="Todo text cannot be empty")
            if len(todo_update.text.strip()) > 500:
                raise HTTPException(status_code=400, detail="Todo text cannot exceed 500 characters")
            todo.text = todo_update.text.strip()
        
        if todo_update.completed is not None:
            todo.completed = todo_update.completed
        
        db.commit()
        db.refresh(todo)
        
        logger.info(f"Updated todo {todo_id}")
        return todo
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update todo: {str(e)}")

@app.delete("/todos/{todo_id}", tags=["Todos"])
async def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    """Delete a todo"""
    try:
        logger.info(f"Deleting todo with ID: {todo_id}")
        todo = db.query(TodoDB).filter(TodoDB.id == todo_id).first()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        db.delete(todo)
        db.commit()
        
        logger.info(f"Deleted todo {todo_id}")
        return {"message": "Todo deleted successfully"}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete todo: {str(e)}")

# Global exception handler with more detailed logging
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal server error")

# Startup event to ensure database is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Starting Todo API server...")
    try:
        # Test database connection on startup using text() for raw SQL
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection verified on startup")
    except Exception as e:
        logger.error(f"Database connection failed on startup: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Todo API server...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False,
        log_level="info"
    )