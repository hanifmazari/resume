

from app import generate_resume
from src.BestResumeMaker.components.ai_helper import (analyze_resume_against_jd,
                                                       enhance_professional_experience,
                                                       enhance_profile_summary, enhance_project_description)
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Callable
import os
import tempfile
from datetime import datetime
import uuid
import logging
import time
import json
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", 8000))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", 52428800))  # 50MB default
RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", 100))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", 60))
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
TEMP_DIR = os.getenv("TEMP_DIR", tempfile.gettempdir())

# CORS and security settings
# CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000, ").split(",")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else []

logger.info(f"Environment: {ENVIRONMENT}")
logger.info(f"Debug mode: {DEBUG}")
# logger.info(f"CORS origins: {CORS_ORIGINS}")
logger.info(f"Allowed hosts: {ALLOWED_HOSTS}")

# Custom Middleware Classes
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Only add HSTS in production with HTTPS
        if ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and response status"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Log request
        start_time = time.time()
        client_ip = request.client.host
        method = request.method
        url = str(request.url)
        
        if DEBUG:
            logger.debug(f"[{request_id}] {method} {url} - IP: {client_ip} - Started")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            log_level = logging.DEBUG if response.status_code < 400 else logging.INFO
            logger.log(log_level,
                f"[{request_id}] {method} {url} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.3f}s - "
                f"IP: {client_ip}"
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] {method} {url} - "
                f"ERROR: {str(e)} - "
                f"Duration: {duration:.3f}s - "
                f"IP: {client_ip}"
            )
            raise

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent abuse"""
    
    def __init__(self, app, max_size: int = MAX_REQUEST_SIZE):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
                raise HTTPException(
                    status_code=413,
                    detail=f"Request too large. Max size: {self.max_size} bytes"
                )
        
        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware"""
    
    def __init__(self, app, calls: int = RATE_LIMIT_CALLS, period: int = RATE_LIMIT_PERIOD):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks in development
        if DEBUG and request.url.path in ["/health", "/test"]:
            return await call_next(request)
            
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean old entries
        if client_ip in self.clients:
            self.clients[client_ip] = [
                timestamp for timestamp in self.clients[client_ip]
                if current_time - timestamp < self.period
            ]
        else:
            self.clients[client_ip] = []
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.calls} calls per {self.period} seconds"
            )
        
        # Add current request
        self.clients[client_ip].append(current_time)
        
        return await call_next(request)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch and log unhandled exceptions"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            # Re-raise to let FastAPI handle it
            raise

class APIMonitoringMiddleware(BaseHTTPMiddleware):
    """Monitor API performance and errors"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log metrics
            duration = time.time() - start_time
            endpoint = request.url.path
            method = request.method
            status_code = response.status_code
            
            # Log slow requests
            if duration > 5.0:  # Log requests taking more than 5 seconds
                logger.warning(f"SLOW_REQUEST: {method} {endpoint} {status_code} {duration:.3f}s")
            elif DEBUG:
                logger.debug(f"API_METRIC: {method} {endpoint} {status_code} {duration:.3f}s")
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"API_ERROR: {request.method} {request.url.path} {duration:.3f}s - {str(e)}")
            raise

# Initialize FastAPI app
app = FastAPI(
    title="Best Resume Maker API",
    description="API for generating professional resumes and analyzing them against job descriptions",
    version="1.0.0",
    debug=DEBUG,
    docs_url="/docs" if DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if DEBUG else None,  # Disable redoc in production
)

# Rate limit records for dependency-based rate limiting
rate_limit_records = defaultdict(float)

# Add middlewares in order (last added = first executed)

# 1. Error handling (should be first/outermost)
app.add_middleware(ErrorHandlingMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Request logging
app.add_middleware(RequestLoggingMiddleware)

# 4. API monitoring
app.add_middleware(APIMonitoringMiddleware)

# 5. Request size limiting
app.add_middleware(RequestSizeLimitMiddleware, max_size=MAX_REQUEST_SIZE)

# 6. Global rate limiting (optional - uncomment if you want global rate limiting)
# app.add_middleware(RateLimitMiddleware, calls=RATE_LIMIT_CALLS, period=RATE_LIMIT_PERIOD)

# 7. GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 8. Trusted hosts (for production)
if ENVIRONMENT == "production" and ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    logger.info(f"Trusted hosts configured: {ALLOWED_HOSTS}")

# 9. Session middleware (uncomment if you need sessions)
# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# 10. CORS (should be last/innermost for proper handling)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=CORS_ORIGINS,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class TextRequest(BaseModel):
    text: str

# Dependency for rate limiting (keeping your existing approach)
async def rate_limiter(request: Request):
    client_ip = request.client.host
    current_time = time.time()

    if current_time - rate_limit_records[client_ip] < 5:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    rate_limit_records[client_ip] = current_time
    if DEBUG:
        logger.debug(f"Request from {client_ip} allowed at {current_time}")

def validate_required_fields(data: dict):
    """Validate that required fields are present"""
    if not isinstance(data, dict):
        return ["Invalid data format"]
    
    # Required fields
    required_fields = ['personal_info', 'professional_summary']
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    # Additional validation for personal_info structure
    if 'personal_info' in data and data['personal_info']:
        personal_info = data['personal_info']
        if not isinstance(personal_info, dict):
            missing_fields.append("personal_info must be a dictionary")
        elif not personal_info.get('name'):
            missing_fields.append("personal_info.name is required")
    
    return missing_fields

def cleanup_file(file_path: str):
    """Clean up generated file"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up file: {file_path}")
    except Exception as e:
        logger.warning(f"Could not clean up file {file_path}: {e}")

# API Endpoints
@app.post("/generate-resume")
async def create_resume(request: Request, background_tasks: BackgroundTasks, dep=Depends(rate_limiter)):
    """Generate a resume based on provided data"""
    start_time = datetime.now()
    try:
        logger.info("=== RESUME GENERATION STARTED ===")
        logger.info(f"Request received at: {start_time}")
        
        data = await request.json()
        if not data:
            raise HTTPException(status_code=400, detail="No data provided")

        # Validate required fields
        missing_fields = validate_required_fields(data)
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Missing required fields",
                    "missing_fields": missing_fields
                }
            )

        # Extract required fields
        template_name = data.get('template_name')
        personal_info = data['personal_info']  # Required
        professional_summary = data['professional_summary']  # Required
        
        # Extract optional fields with defaults
        work_experience = data.get('work_experience', [])
        education = data.get('education', [])
        skills = data.get('skills', [])
        profile_picture = data.get("profile_picture")
        academic_projects = data.get('academic_projects', [])
        certifications = data.get('certifications', [])
        publications = data.get('publications', [])
        hobbies = data.get('hobbies', [])
        languages = data.get('languages', [])
        referees = data.get('referees', [])
        page_size = data.get('page_size', 'A4')

        user_name = personal_info.get('name', 'Unknown User')
        logger.info(f"Generating resume for: {user_name}")

        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"resume_{unique_id}.pdf"
        
        # Use configured temp directory
        output_path = os.path.join(TEMP_DIR, output_filename)
        
        logger.info(f"Output path: {output_path}")
        logger.info(f"Temp directory: {TEMP_DIR}")
        
        # Log processing time before generation
        pre_generation_time = datetime.now()
        logger.info(f"Starting PDF generation at: {pre_generation_time}")
        
        # Generate resume with timeout handling
        try:
            success = generate_resume(
                template_name=template_name,
                personal_info=personal_info,
                professional_summary=professional_summary,
                work_experience=work_experience,
                education=education,
                skills=skills,
                profile_picture=profile_picture,
                academic_projects=academic_projects,
                certifications=certifications,
                publications=publications,
                hobbies=hobbies,
                languages=languages,
                referees=referees,
                output_file=output_path,
                page_size=page_size
            )
        except Exception as gen_error:
            logger.error(f"Resume generation failed: {str(gen_error)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Resume generation failed: {str(gen_error)}")

        post_generation_time = datetime.now()
        generation_duration = (post_generation_time - pre_generation_time).total_seconds()
        logger.info(f"PDF generation completed at: {post_generation_time}")
        logger.info(f"Generation took: {generation_duration:.2f} seconds")
        
        if not success:
            logger.error("Resume generation returned False")
            raise HTTPException(status_code=500, detail="Failed to generate resume")

        # Check if file was created
        if not os.path.exists(output_path):
            logger.error(f"Resume file not found at: {output_path}")
            # List files in temp directory for debugging
            try:
                temp_files = os.listdir(TEMP_DIR)
                logger.info(f"Files in temp directory: {temp_files}")
            except:
                logger.info("Could not list temp directory contents")
            raise HTTPException(status_code=500, detail="Resume file was not created")

        file_size = os.path.getsize(output_path)
        logger.info(f"Resume file created successfully - Size: {file_size} bytes")

        if file_size == 0:
            logger.error("Generated resume file is empty")
            raise HTTPException(status_code=500, detail="Generated resume file is empty")

        # Add cleanup task to run after response is sent
        background_tasks.add_task(cleanup_file, output_path)

        # Return the file
        filename = f"{user_name.replace(' ', '_')}_Resume.pdf"
        
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== RESUME GENERATION COMPLETED ===")
        logger.info(f"Total processing time: {total_duration:.2f} seconds")
        logger.info(f"Returning file: {filename}")
        
        return FileResponse(
            path=output_path,
            media_type='application/pdf',
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        total_duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"=== RESUME GENERATION FAILED ===")
        logger.error(f"Total processing time before error: {total_duration:.2f} seconds")
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "service": "Best Resume Maker API",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "uptime": "Service is running"
    }

@app.get("/test")
async def test_endpoint():
    """Quick test endpoint to verify API is working"""
    logger.debug("Test endpoint called")
    return {
        "message": "API is working correctly",
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "environment": ENVIRONMENT
    }

@app.post("/enhance_experience")
async def enhance_experience(request: TextRequest, dep=Depends(rate_limiter)):
    """Enhance professional experience description"""
    try:
        logger.info("Experience enhancement requested")
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text field cannot be empty")
        
        result = enhance_professional_experience(request.text)
        logger.info("Experience enhancement completed successfully")
        return {"enhanced_experience": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enhancing experience: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/enhance_summary")
async def enhance_summary(request: TextRequest, dep=Depends(rate_limiter)):
    """Enhance profile summary"""
    try:
        logger.info("Summary enhancement requested")
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text field cannot be empty")
        
        result = enhance_profile_summary(request.text)
        logger.info("Summary enhancement completed successfully")
        return {"enhanced_summary": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enhancing summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/enhance_project")
async def enhance_project(request: TextRequest, dep=Depends(rate_limiter)):
    """Enhance project description"""
    try:
        logger.info("Project enhancement requested")
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text field cannot be empty")
        
        result = enhance_project_description(request.text)
        logger.info("Project enhancement completed successfully")
        return {"enhanced_project_description": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enhancing project: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post('/analyze-resume')
async def analyze_resume_api(
    resume: UploadFile = File(..., description="Resume file to analyze"),
    job_description: str = Form(..., description="Job description to compare against"), dep=Depends(rate_limiter)
):
    # if resume.content_type != "application/pdf":
    #     raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    """Analyze a resume against a job description"""
    logger.info("Resume analysis requested")
    
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is empty")
    
    try:
        # Read the uploaded file
        resume_content = await resume.read()
        logger.info(f"Resume file read, size: {len(resume_content)} bytes")
        
        # Analyze resume against job description
        result = analyze_resume_against_jd(resume_content, job_description)
        logger.info("Resume analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Error occurred during analyzing resume: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Best Resume Maker API",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "domain": "bestresumemaker.com",
        "endpoints": {
            "health": "/health",
            "test": "/test",
            "generate_resume": "/generate-resume",
            "analyze_resume": "/analyze-resume",
            "enhance_experience": "/enhance_experience",
            "enhance_summary": "/enhance_summary",
            "enhance_project": "/enhance_project",
            "docs": "/docs" if DEBUG else "disabled",
            "redoc": "/redoc" if DEBUG else "disabled"
        }
    }
# Fix 1: Modify the __main__ section to use import string
if __name__ == '__main__':
    import uvicorn
    logger.info(f"Starting Best Resume Maker API server on 0.0.0.0:{PORT}")
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"Debug mode: {DEBUG}")
    
    # Use import string instead of app object for reload to work
    uvicorn.run(
        "app2:app",  # Replace "app2" with your actual filename
        host="0.0.0.0", 
        port=PORT, 
        reload=True,  # Only use reload in debug mode
        log_level="info" if not DEBUG else "debug"
    )
