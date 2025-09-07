from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time
import uuid

@dataclass
class Job:
    job_id: str
    source: str
    created_at: float
    updated_at: float
    status: str = "pending"
    files: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class JobTracker:
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        
    def create_job(self, source: str = "api", metadata: Optional[Dict] = None) -> str:
        """Create a new job"""
        job_id = f"{source}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        now = time.time()
        
        job = Job(
            job_id=job_id,
            source=source,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )
        
        self.jobs[job_id] = job
        return job_id
    
    def update_job(self, job_id: str, status: Optional[str] = None, 
                   files: Optional[List[Dict]] = None) -> bool:
        """Update job status and/or files"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        job.updated_at = time.time()
        
        if status:
            job.status = status
        if files:
            job.files.extend(files)
        
        return True
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a specific job"""
        return self.jobs.get(job_id)
    
    def get_recent_jobs(self, limit: int = 10, source: Optional[str] = None) -> List[Job]:
        """Get recent jobs, optionally filtered by source"""
        jobs = list(self.jobs.values())
        
        if source:
            jobs = [j for j in jobs if j.source == source]
        
        # Sort by updated_at descending
        jobs.sort(key=lambda x: x.updated_at, reverse=True)
        
        return jobs[:limit]

# Global instance
job_tracker = JobTracker()