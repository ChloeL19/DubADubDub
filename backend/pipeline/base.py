from abc import ABC, abstractmethod
from typing import Dict, Any
import logging
import time


class PipelineError(Exception):
    """Base exception for all pipeline errors"""
    def __init__(self, stage: str, error_type: str, message: str, retry_possible: bool = True):
        self.stage = stage
        self.error_type = error_type  # 'api_error', 'file_format', 'model_error', 'network_error'
        self.message = message
        self.retry_possible = retry_possible
        super().__init__(f"{stage}: {error_type} - {message}")


class APIError(PipelineError):
    """API-related errors (rate limits, authentication, etc.)"""
    pass


class FileError(PipelineError):
    """File processing errors (format, corruption, etc.)"""
    pass


class ModelError(PipelineError):
    """Model loading/processing errors"""
    pass


class PipelineStage(ABC):
    """Abstract base for all pipeline stages"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        pass
    
    def log_stage_start(self, stage_name: str, input_info: str):
        self.logger.info(f"Starting {stage_name}: {input_info}")
    
    def log_stage_complete(self, stage_name: str, output_info: str):
        self.logger.info(f"Completed {stage_name}: {output_info}")
    
    def log_error(self, stage_name: str, error: Exception):
        self.logger.error(f"Error in {stage_name}: {str(error)}")