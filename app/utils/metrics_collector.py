"""
Performance Metrics Collector

Centralized system for collecting and tracking performance metrics
across audio processing, LLM inference, and database operations.
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class MetricEntry:
    """Single metric entry."""
    timestamp: float
    metric_name: str
    value: float
    unit: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class MetricsCollector:
    """Collects and stores performance metrics."""
    
    def __init__(self, output_dir: str = "tests/results"):
        self.output_dir = output_dir
        self.metrics: list[MetricEntry] = []
        self.timers: Dict[str, float] = {}
        os.makedirs(output_dir, exist_ok=True)
    
    def start_timer(self, name: str):
        """Start a named timer."""
        self.timers[name] = time.time()
    
    def end_timer(self, name: str, metadata: Dict[str, Any] = None) -> float:
        """End a named timer and record the duration."""
        if name not in self.timers:
            logger.warning(f"Timer '{name}' was not started")
            return 0.0
        
        duration = time.time() - self.timers[name]
        del self.timers[name]
        
        self.record_metric(
            metric_name=name,
            value=duration,
            unit="seconds",
            metadata=metadata or {}
        )
        
        return duration
    
    def record_metric(self, metric_name: str, value: float, unit: str, metadata: Dict[str, Any] = None):
        """Record a metric value."""
        entry = MetricEntry(
            timestamp=time.time(),
            metric_name=metric_name,
            value=value,
            unit=unit,
            metadata=metadata or {}
        )
        self.metrics.append(entry)
        logger.debug(f"Metric recorded: {metric_name}={value}{unit}")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage."""
        process = psutil.Process()
        mem_info = process.memory_info()
        
        return {
            "rss_mb": mem_info.rss / 1024 / 1024,  # Resident Set Size
            "vms_mb": mem_info.vms / 1024 / 1024,  # Virtual Memory Size
            "percent": process.memory_percent()
        }
    
    def record_memory_snapshot(self, label: str):
        """Record current memory usage."""
        mem = self.get_memory_usage()
        self.record_metric(
            metric_name=f"memory_{label}",
            value=mem["rss_mb"],
            unit="MB",
            metadata={"vms_mb": mem["vms_mb"], "percent": mem["percent"]}
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all metrics."""
        summary = {}
        
        # Group metrics by name
        grouped = {}
        for entry in self.metrics:
            if entry.metric_name not in grouped:
                grouped[entry.metric_name] = []
            grouped[entry.metric_name].append(entry.value)
        
        # Calculate statistics
        for name, values in grouped.items():
            if not values:
                continue
            
            summary[name] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "total": sum(values),
                "unit": next((m.unit for m in self.metrics if m.metric_name == name), "")
            }
        
        return summary
    
    def save_to_file(self, filename: str = None):
        """Save metrics to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_summary(),
            "raw_metrics": [asdict(m) for m in self.metrics]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")
        return filepath
    
    def clear(self):
        """Clear all collected metrics."""
        self.metrics.clear()
        self.timers.clear()


# Global instance
_global_collector = None

def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
