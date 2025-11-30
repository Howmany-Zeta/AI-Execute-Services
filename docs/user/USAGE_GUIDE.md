# AIECS Usage Guide

## 🔧 Three Usage Modes Explained

### 1️⃣ **Standalone Service Mode**

Use Cases:
- Need to run complete AI middleware service
- Support multiple client connections
- Need WebSocket real-time communication
- Need distributed task processing

#### 🚀 Start Service

```bash
# Method 1: Use command-line entry (recommended)
aiecs

# Method 2: Use Python module
python -m aiecs

# Method 3: Use uvicorn directly
uvicorn aiecs.main:app --host 0.0.0.0 --port 8000

# Method 4: Use poetry
poetry run python -m aiecs
```

#### 🔧 Start Complete Distributed Environment

```bash
# 1. Start Redis (message queue)
redis-server

# 2. Start PostgreSQL database
sudo systemctl start postgresql

# 3. Start main service (FastAPI + WebSocket)
aiecs

# 4. Start Celery Worker (process async tasks)
celery -A aiecs.tasks.worker.celery_app worker --loglevel=info

# 5. Start Celery Beat (scheduled task scheduler)
celery -A aiecs.tasks.worker.celery_app beat --loglevel=info

# 6. Start Flower (Celery monitoring interface)
celery -A aiecs.tasks.worker.celery_app flower --port=5555
```

#### 📡 Client Calls

```python
import httpx
import asyncio

async def call_aiecs_service():
    async with httpx.AsyncClient() as client:
        # Call health check
        health = await client.get("http://localhost:8000/health")
        print(health.json())
        
        # Get available tools
        tools = await client.get("http://localhost:8000/api/tools")
        print(tools.json())
        
        # Execute task
        task_data = {
            "type": "task",
            "mode": "execute", 
            "service": "default",
            "userId": "user123",
            "context": {
                "metadata": {
                    "aiPreference": {
                        "provider": "OpenAI",
                        "model": "gpt-4"
                    }
                },
                "data": {
                    "task": "Analyze this text",
                    "content": "Hello world"
                }
            }
        }
        
        response = await client.post(
            "http://localhost:8000/api/execute",
            json=task_data
        )
        result = response.json()
        print(f"Task ID: {result['taskId']}")

# Run
asyncio.run(call_aiecs_service())
```

#### 🌐 WebSocket Client

```javascript
// Node.js or browser
const io = require('socket.io-client');

const socket = io('http://localhost:8000');

socket.on('connect', () => {
    console.log('Connected to AIECS');
    
    // Register user to receive updates
    socket.emit('register', { user_id: 'user123' });
});

socket.on('progress', (data) => {
    console.log('Task progress:', data);
});

socket.on('task_complete', (data) => {
    console.log('Task completed:', data);
});
```

---

### 2️⃣ **Library Import Mode**

Use Cases:
- Integrate into existing Python applications
- Need fine-grained control
- Custom configuration and initialization
- Embedded usage

#### 📦 Basic Library Usage

```python
import asyncio
from aiecs import AIECS, TaskContext, validate_required_settings

async def main():
    # Check configuration (optional)
    try:
        validate_required_settings("llm")
        print("LLM configuration check passed")
    except ValueError as e:
        print(f"Configuration missing: {e}")
        return
    
    # Create client
    client = AIECS()
    
    try:
        # Initialize service
        await client.initialize()
        
        # Create task context
        context = TaskContext({
            "user_id": "user123",
            "metadata": {
                "aiPreference": {
                    "provider": "OpenAI",
                    "model": "gpt-4"
                }
            },
            "data": {
                "task": "Analyze the sentiment of this text",
                "content": "The weather is great today, feeling very happy!"
            }
        })
        
        # Execute task
        result = await client.execute(context)
        print(f"Task result: {result}")
        
        # Execute tools directly
        tools = await client.get_available_tools()
        print(f"Available tools: {len(tools)}")
        
        # Execute specific tool
        if tools:
            tool_result = await client.execute_tool(
                "scraper_tool", 
                "scrape_url", 
                {"url": "https://example.com"}
            )
            print(f"Tool execution result: {tool_result}")
    
    finally:
        # Cleanup resources
        await client.close()

# Run
asyncio.run(main())
```

#### 🎯 Using Session Context Manager (Recommended)

```python
import asyncio
from aiecs import AIECS, TaskContext

async def main():
    # Use context manager to automatically manage resources
    async with AIECS().session() as client:
        # Get tool
        scraper_tool = await client.get_tool("scraper_tool")
        
        # Call tool method directly
        result = await scraper_tool.run_async("scrape_url", 
            url="https://news.ycombinator.com",
            extract=["title", "links"]
        )
        
        print(f"Scraping result: {result}")

asyncio.run(main())
```

#### 🔧 Custom Configuration

```python
from aiecs import AIECS

# Custom configuration
custom_config = {
    "rate_limit_requests_per_second": 10,
    "max_retries": 3,
    "timeout": 60
}

async with AIECS(config=custom_config).session() as client:
    # Use client with custom configuration
    result = await client.execute_tool(
        "research_tool",
        "search",
        {"query": "AI middleware patterns", "max_results": 5}
    )
```

---

### 3️⃣ **FastAPI Integration Mode**

Use Cases:
- Have existing FastAPI application, want to integrate AI functionality
- Need custom routes and middleware
- Want complete control over application architecture
- Component in microservice architecture

#### 🏗️ Sub-Application Mounting

```python
# your_main_app.py
from fastapi import FastAPI
from aiecs import get_fastapi_app

# Create main application
app = FastAPI(title="My Main Application")

# Mount AIECS application
aiecs_app = get_fastapi_app()
app.mount("/ai", aiecs_app)

# Add your own routes
@app.get("/")
async def root():
    return {"message": "Main application homepage"}

@app.get("/custom")  
async def custom_endpoint():
    return {"service": "custom", "status": "active"}

# Now you can access:
# http://localhost:8000/          -> Main application
# http://localhost:8000/custom    -> Custom endpoint
# http://localhost:8000/ai/health -> AIECS health check
# http://localhost:8000/ai/api/tools -> AIECS tools list
```

#### 🔗 Component-Level Integration

```python
# advanced_integration.py
from fastapi import FastAPI, HTTPException, Depends
from aiecs import AIECS, TaskContext, get_settings, validate_required_settings
from aiecs.tools import get_tool
from typing import Dict, Any

app = FastAPI(title="AI-Enhanced Application")

# Global AIECS client
aiecs_client = None

@app.on_event("startup")
async def startup():
    global aiecs_client
    # Validate required configuration
    try:
        validate_required_settings("llm")
    except ValueError as e:
        print(f"Configuration missing, AI functionality will be unavailable: {e}")
        return
    
    # Initialize AIECS client
    aiecs_client = AIECS()
    await aiecs_client.initialize()

@app.on_event("shutdown") 
async def shutdown():
    global aiecs_client
    if aiecs_client:
        await aiecs_client.close()

# Dependency injection
async def get_aiecs_client():
    if not aiecs_client:
        raise HTTPException(status_code=503, detail="AI service unavailable")
    return aiecs_client

# Custom AI endpoint
@app.post("/api/analyze")
async def analyze_text(
    data: Dict[str, Any],
    client: AIECS = Depends(get_aiecs_client)
):
    """Text analysis API"""
    context = TaskContext({
        "user_id": data.get("user_id", "anonymous"),
        "metadata": {
            "aiPreference": {
                "provider": "OpenAI", 
                "model": "gpt-4"
            }
        },
        "data": {
            "task": "Analyze text sentiment and keywords",
            "content": data["text"]
        }
    })
    
    result = await client.execute(context)
    return {"analysis": result}

@app.post("/api/scrape")
async def scrape_website(
    data: Dict[str, Any],
    client: AIECS = Depends(get_aiecs_client)
):
    """Web scraping API"""
    result = await client.execute_tool(
        "scraper_tool",
        "scrape_url", 
        {
            "url": data["url"],
            "extract": data.get("extract", ["title", "content"])
        }
    )
    return {"scraped_data": result}

@app.get("/api/tools")
async def get_available_tools(client: AIECS = Depends(get_aiecs_client)):
    """Get available tools"""
    tools = await client.get_available_tools()
    return {"tools": tools}
```

#### 🎛️ Selective Feature Integration

```python
# selective_integration.py
from fastapi import FastAPI
from aiecs.tools import discover_tools, get_tool
from aiecs.config.config import get_settings

app = FastAPI(title="Lightweight AI Application")

# Only use tool system, don't start complete service
@app.on_event("startup")
async def startup():
    # Discover and register tools
    discover_tools("aiecs.tools")
    print("Tool system initialized")

@app.post("/api/quick-scrape")
async def quick_scrape(url: str):
    """Quick web scraping (without using complete task queue)"""
    try:
        scraper = get_tool("scraper_tool")
        result = await scraper.run_async("scrape_url", url=url)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/analyze-document")
async def analyze_document(file_path: str):
    """Document analysis"""
    try:
        office_tool = get_tool("office_tool") 
        result = await office_tool.run_async("extract_text", file_path=file_path)
        })
        return {"text": result}
    except Exception as e:
        return {"error": str(e)}
```

---

## 🔄 **Usage Mode Comparison**

| Feature | Standalone Service | Library Import | FastAPI Integration |
|---------|-------------------|----------------|-------------------|
| **Complexity** | Simple | Medium | High |
| **Control Level** | Low | High | Highest |
| **Resource Consumption** | High | Medium | Controllable |
| **Distributed Support** | ✅ Complete | ✅ Complete | 🔧 Optional |
| **WebSocket** | ✅ Built-in | ❌ Manual | 🔧 Optional |
| **Custom Routes** | ❌ Fixed | ❌ None | ✅ Complete |
| **Startup Time** | Slow | Fast | Controllable |

---

## ⚙️ **Environment Configuration**

### **Minimum Configuration (Library Usage)**
```env
# Configure at least one LLM provider
OPENAI_API_KEY=your_openai_key

# Redis (if using async tasks)
CELERY_BROKER_URL=redis://localhost:6379/0
```

### **Complete Configuration (Standalone Service)**
```env
# LLM Providers
OPENAI_API_KEY=your_openai_key
VERTEX_PROJECT_ID=your_gcp_project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
XAI_API_KEY=your_xai_key

# Infrastructure
CELERY_BROKER_URL=redis://localhost:6379/0
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_NAME=aiecs
DB_PORT=5432

# Google Cloud Storage (optional)
GOOGLE_CLOUD_PROJECT_ID=your_project
GOOGLE_CLOUD_STORAGE_BUCKET=your_bucket

# CORS (set specific domain in production)
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### **Docker Quick Start**
```yaml
# docker-compose.yml
version: '3.8'
services:
  aiecs:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CELERY_BROKER_URL=redis://redis:6379/0
      - DB_HOST=postgres
      - DB_USER=aiecs
      - DB_PASSWORD=password
      - DB_NAME=aiecs
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: aiecs
      POSTGRES_USER: aiecs  
      POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 🎯 **Selection Recommendations**

### **Choose Standalone Service, when:**
- Need to provide AI services for multiple applications
- Need WebSocket real-time communication
- Team wants an out-of-the-box solution
- Need Celery distributed task processing

### **Choose Library Import, when:**
- Integrating into existing Python applications
- Need fine-grained control and customization
- Only need core AI functionality
- Want lightweight deployment

### **Choose FastAPI Integration, when:**
- Have existing FastAPI application
- Need custom API endpoints
- Want complete control over architecture
- Need to mix AI and business logic

---

## 🛠️ **Development and Debugging**

```bash
# Development mode startup (auto-reload)
RELOAD=true aiecs

# Or
uvicorn aiecs.main:app --reload --host 0.0.0.0 --port 8000

# Check tool availability
python -c "from aiecs import list_tools; print(list_tools())"

# Validate specific configuration
python -c "from aiecs import validate_required_settings; validate_required_settings('llm')"

# Check version
python -c "import aiecs; print(aiecs.__version__)"
```

---

## 🔍 **Troubleshooting**

### **Common Issues:**

1. **Import Failure**:
   ```bash
   # Check dependencies
   pip install aiecs
   
   # Check version
   python -c "import aiecs; print('OK')"
   ```

2. **Configuration Error**:
   ```python
   from aiecs import validate_required_settings
   validate_required_settings("basic")  # Only check basic functionality
   ```

3. **Service Startup Failure**:
   ```bash
   # Check port
   netstat -tulpn | grep :8000
   
   # Check Redis
   redis-cli ping
   
   # Check database
   psql -h localhost -U postgres -d aiecs -c "\dt"
   ```

4. **Tool Execution Failure**:
   ```python
   # Check specific tool
   from aiecs import get_tool
   tool = get_tool("scraper_tool")
   print(tool.describe())  # View tool description
   ```

This way, users can choose the most suitable usage mode based on their needs!
