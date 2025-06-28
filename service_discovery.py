"""
Service Discovery Module for Azure OpenAI Agents

This module provides comprehensive service discovery functionality including:
- Dynamic endpoint management
- Health checking with circuit breaker pattern
- Load balancing with multiple algorithms
- Automatic failover and recovery
- Service registry with runtime configuration
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import aiohttp
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EndpointStatus(Enum):
    """Endpoint health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DISABLED = "disabled"


class LoadBalancerAlgorithm(Enum):
    """Load balancing algorithm options"""
    PRIORITY = "priority"
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    PRIORITY_WITH_FALLBACK = "priority_with_fallback"


class CircuitBreakerState(Enum):
    """Circuit breaker state enumeration"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class EndpointConfig:
    """Configuration for a service endpoint"""
    name: str
    endpoint: str
    api_key: str
    priority: int = 1
    weight: int = 1
    health_check_url: str = "/models"
    timeout: int = 30
    max_connections: int = 100
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckConfig:
    """Configuration for health checking"""
    interval: int = 30  # seconds
    timeout: int = 10  # seconds
    retries: int = 3
    failure_threshold: int = 3
    success_threshold: int = 2
    expected_status_codes: List[int] = field(default_factory=lambda: [200, 401])


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    success_threshold: int = 3
    half_open_max_calls: int = 5


@dataclass
class LoadBalancerConfig:
    """Configuration for load balancer"""
    algorithm: LoadBalancerAlgorithm = LoadBalancerAlgorithm.PRIORITY_WITH_FALLBACK
    sticky_sessions: bool = False
    connection_pooling: bool = True
    request_timeout: int = 30
    max_retries: int = 3
    backoff_strategy: str = "exponential"
    retry_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504, 429])


@dataclass
class EndpointMetrics:
    """Metrics for an endpoint"""
    name: str
    status: EndpointStatus = EndpointStatus.UNKNOWN
    last_check: Optional[datetime] = None
    response_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    active_connections: int = 0
    last_error: Optional[str] = None
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    circuit_breaker_failures: int = 0
    circuit_breaker_last_failure: Optional[datetime] = None


class HealthMonitor:
    """Health monitoring for service endpoints"""
    
    def __init__(self, config: HealthCheckConfig):
        self.config = config
        self.metrics: Dict[str, EndpointMetrics] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start_monitoring(self, endpoints: List[EndpointConfig]):
        """Start health monitoring for all endpoints"""
        if self._running:
            return
            
        self._running = True
        for endpoint in endpoints:
            if endpoint.enabled:
                self.metrics[endpoint.name] = EndpointMetrics(name=endpoint.name)
                task = asyncio.create_task(self._monitor_endpoint(endpoint))
                self._tasks.append(task)
        
        logger.info(f"Started health monitoring for {len(endpoints)} endpoints")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Stopped health monitoring")
    
    async def _monitor_endpoint(self, endpoint: EndpointConfig):
        """Monitor a single endpoint continuously"""
        while self._running:
            try:
                await self._check_endpoint_health(endpoint)
                await asyncio.sleep(self.config.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring endpoint {endpoint.name}: {e}")
                await asyncio.sleep(self.config.interval)
    
    async def _check_endpoint_health(self, endpoint: EndpointConfig):
        """Perform health check for a single endpoint"""
        metrics = self.metrics.get(endpoint.name)
        if not metrics:
            return
        
        start_time = time.time()
        success = False
        error_msg = None
        
        try:
            # Perform health check with retries
            for attempt in range(self.config.retries):
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                        url = f"{endpoint.endpoint.rstrip('/')}{endpoint.health_check_url}"
                        headers = {"Authorization": f"Bearer {endpoint.api_key}"}
                        
                        async with session.get(url, headers=headers) as response:
                            response_time = time.time() - start_time
                            
                            if response.status in self.config.expected_status_codes:
                                success = True
                                self._update_success_metrics(metrics, response_time)
                                break
                            else:
                                error_msg = f"Unexpected status code: {response.status}"
                
                except asyncio.TimeoutError:
                    error_msg = "Request timeout"
                except Exception as e:
                    error_msg = str(e)
                
                if attempt < self.config.retries - 1:
                    await asyncio.sleep(1)  # Brief delay between retries
        
        except Exception as e:
            error_msg = f"Health check failed: {e}"
        
        if not success:
            self._update_failure_metrics(metrics, error_msg)
        
        metrics.last_check = datetime.now()
        self._update_endpoint_status(metrics)
    
    def _update_success_metrics(self, metrics: EndpointMetrics, response_time: float):
        """Update metrics after successful health check"""
        metrics.success_count += 1
        metrics.total_requests += 1
        metrics.response_time = response_time
        metrics.last_error = None
        metrics.circuit_breaker_failures = 0
    
    def _update_failure_metrics(self, metrics: EndpointMetrics, error_msg: str):
        """Update metrics after failed health check"""
        metrics.failure_count += 1
        metrics.total_requests += 1
        metrics.last_error = error_msg
        metrics.circuit_breaker_failures += 1
        metrics.circuit_breaker_last_failure = datetime.now()
    
    def _update_endpoint_status(self, metrics: EndpointMetrics):
        """Update endpoint status based on recent health checks"""
        consecutive_failures = metrics.circuit_breaker_failures
        consecutive_successes = metrics.success_count - (metrics.failure_count - consecutive_failures)
        
        if consecutive_failures >= self.config.failure_threshold:
            metrics.status = EndpointStatus.UNHEALTHY
            metrics.circuit_breaker_state = CircuitBreakerState.OPEN
        elif consecutive_successes >= self.config.success_threshold:
            metrics.status = EndpointStatus.HEALTHY
            metrics.circuit_breaker_state = CircuitBreakerState.CLOSED
        
        logger.debug(f"Endpoint {metrics.name} status: {metrics.status}")
    
    def get_endpoint_metrics(self, endpoint_name: str) -> Optional[EndpointMetrics]:
        """Get metrics for a specific endpoint"""
        return self.metrics.get(endpoint_name)
    
    def get_healthy_endpoints(self) -> List[str]:
        """Get list of healthy endpoint names"""
        return [name for name, metrics in self.metrics.items() 
                if metrics.status == EndpointStatus.HEALTHY]


class LoadBalancer:
    """Load balancer with multiple algorithms and failover support"""
    
    def __init__(self, config: LoadBalancerConfig):
        self.config = config
        self._round_robin_index = 0
        self._connection_counts: Dict[str, int] = {}
    
    def select_endpoint(self, endpoints: List[EndpointConfig], 
                       health_monitor: HealthMonitor) -> Optional[EndpointConfig]:
        """Select the best endpoint based on the configured algorithm"""
        healthy_endpoints = self._filter_healthy_endpoints(endpoints, health_monitor)
        
        if not healthy_endpoints:
            logger.warning("No healthy endpoints available")
            return None
        
        if self.config.algorithm == LoadBalancerAlgorithm.PRIORITY:
            return self._select_by_priority(healthy_endpoints)
        elif self.config.algorithm == LoadBalancerAlgorithm.ROUND_ROBIN:
            return self._select_round_robin(healthy_endpoints)
        elif self.config.algorithm == LoadBalancerAlgorithm.LEAST_CONNECTIONS:
            return self._select_least_connections(healthy_endpoints)
        elif self.config.algorithm == LoadBalancerAlgorithm.WEIGHTED:
            return self._select_weighted(healthy_endpoints)
        elif self.config.algorithm == LoadBalancerAlgorithm.PRIORITY_WITH_FALLBACK:
            return self._select_priority_with_fallback(healthy_endpoints)
        else:
            return healthy_endpoints[0] if healthy_endpoints else None
    
    def _filter_healthy_endpoints(self, endpoints: List[EndpointConfig], 
                                 health_monitor: HealthMonitor) -> List[EndpointConfig]:
        """Filter endpoints to only include healthy ones"""
        healthy = []
        for endpoint in endpoints:
            if not endpoint.enabled:
                continue
                
            metrics = health_monitor.get_endpoint_metrics(endpoint.name)
            if metrics and metrics.status == EndpointStatus.HEALTHY:
                healthy.append(endpoint)
        
        return healthy
    
    def _select_by_priority(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select endpoint with highest priority (lowest priority number)"""
        return min(endpoints, key=lambda ep: ep.priority)
    
    def _select_round_robin(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select endpoint using round-robin algorithm"""
        endpoint = endpoints[self._round_robin_index % len(endpoints)]
        self._round_robin_index += 1
        return endpoint
    
    def _select_least_connections(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select endpoint with fewest active connections"""
        return min(endpoints, key=lambda ep: self._connection_counts.get(ep.name, 0))
    
    def _select_weighted(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select endpoint based on weights"""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return endpoints[0]
        
        # Simple weighted selection (could be improved with proper weighted random)
        import random
        weight_sum = 0
        target = random.randint(1, total_weight)
        
        for endpoint in endpoints:
            weight_sum += endpoint.weight
            if weight_sum >= target:
                return endpoint
        
        return endpoints[-1]
    
    def _select_priority_with_fallback(self, endpoints: List[EndpointConfig]) -> EndpointConfig:
        """Select highest priority endpoint, fallback to others if needed"""
        sorted_endpoints = sorted(endpoints, key=lambda ep: ep.priority)
        return sorted_endpoints[0]
    
    def record_connection_start(self, endpoint_name: str):
        """Record that a connection started for an endpoint"""
        self._connection_counts[endpoint_name] = self._connection_counts.get(endpoint_name, 0) + 1
    
    def record_connection_end(self, endpoint_name: str):
        """Record that a connection ended for an endpoint"""
        if endpoint_name in self._connection_counts:
            self._connection_counts[endpoint_name] = max(0, self._connection_counts[endpoint_name] - 1)


class ServiceDiscovery:
    """Main service discovery orchestrator"""
    
    def __init__(self, 
                 health_config: Optional[HealthCheckConfig] = None,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 load_balancer_config: Optional[LoadBalancerConfig] = None):
        self.health_config = health_config or HealthCheckConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.load_balancer_config = load_balancer_config or LoadBalancerConfig()
        
        self.health_monitor = HealthMonitor(self.health_config)
        self.load_balancer = LoadBalancer(self.load_balancer_config)
        
        self.services: Dict[str, List[EndpointConfig]] = {}
        self._initialized = False
    
    async def initialize(self, service_configs: Dict[str, List[Dict[str, Any]]]):
        """Initialize service discovery with endpoint configurations"""
        self.services = {}
        
        for service_name, endpoint_configs in service_configs.items():
            endpoints = []
            for config in endpoint_configs:
                endpoint = EndpointConfig(**config)
                endpoints.append(endpoint)
            self.services[service_name] = endpoints
        
        # Start health monitoring for all endpoints
        all_endpoints = []
        for endpoints in self.services.values():
            all_endpoints.extend(endpoints)
        
        await self.health_monitor.start_monitoring(all_endpoints)
        self._initialized = True
        
        logger.info(f"Service discovery initialized with {len(self.services)} services")
    
    async def shutdown(self):
        """Shutdown service discovery"""
        await self.health_monitor.stop_monitoring()
        self._initialized = False
        logger.info("Service discovery shutdown")
    
    async def get_endpoint(self, service_name: str) -> Optional[EndpointConfig]:
        """Get the best available endpoint for a service"""
        if not self._initialized:
            raise RuntimeError("Service discovery not initialized")
        
        endpoints = self.services.get(service_name, [])
        if not endpoints:
            logger.warning(f"No endpoints configured for service: {service_name}")
            return None
        
        selected = self.load_balancer.select_endpoint(endpoints, self.health_monitor)
        if selected:
            self.load_balancer.record_connection_start(selected.name)
            logger.debug(f"Selected endpoint {selected.name} for service {service_name}")
        
        return selected
    
    def release_endpoint(self, endpoint: EndpointConfig):
        """Release an endpoint connection"""
        self.load_balancer.record_connection_end(endpoint.name)
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get comprehensive status for a service"""
        endpoints = self.services.get(service_name, [])
        status = {
            "service_name": service_name,
            "total_endpoints": len(endpoints),
            "healthy_endpoints": 0,
            "unhealthy_endpoints": 0,
            "endpoints": []
        }
        
        for endpoint in endpoints:
            metrics = self.health_monitor.get_endpoint_metrics(endpoint.name)
            endpoint_status = {
                "name": endpoint.name,
                "endpoint": endpoint.endpoint,
                "priority": endpoint.priority,
                "enabled": endpoint.enabled,
                "status": metrics.status.value if metrics else "unknown",
                "last_check": metrics.last_check.isoformat() if metrics and metrics.last_check else None,
                "response_time": metrics.response_time if metrics else 0,
                "success_rate": (metrics.success_count / max(metrics.total_requests, 1) * 100) if metrics else 0,
                "circuit_breaker_state": metrics.circuit_breaker_state.value if metrics else "unknown"
            }
            
            if metrics and metrics.status == EndpointStatus.HEALTHY:
                status["healthy_endpoints"] += 1
            elif metrics and metrics.status == EndpointStatus.UNHEALTHY:
                status["unhealthy_endpoints"] += 1
            
            status["endpoints"].append(endpoint_status)
        
        return status
    
    def update_endpoint(self, service_name: str, endpoint_name: str, updates: Dict[str, Any]):
        """Update endpoint configuration at runtime"""
        endpoints = self.services.get(service_name, [])
        for endpoint in endpoints:
            if endpoint.name == endpoint_name:
                for key, value in updates.items():
                    if hasattr(endpoint, key):
                        setattr(endpoint, key, value)
                logger.info(f"Updated endpoint {endpoint_name} in service {service_name}")
                break
    
    def disable_endpoint(self, service_name: str, endpoint_name: str):
        """Disable an endpoint temporarily"""
        self.update_endpoint(service_name, endpoint_name, {"enabled": False})
    
    def enable_endpoint(self, service_name: str, endpoint_name: str):
        """Enable an endpoint"""
        self.update_endpoint(service_name, endpoint_name, {"enabled": True})


# Factory functions for easy configuration

def create_service_discovery_from_env() -> ServiceDiscovery:
    """Create service discovery instance from environment variables"""
    
    # Health check configuration
    health_config = HealthCheckConfig(
        interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
        timeout=int(os.getenv("HEALTH_CHECK_TIMEOUT", "10")),
        retries=int(os.getenv("HEALTH_CHECK_RETRIES", "3")),
        failure_threshold=int(os.getenv("HEALTH_CHECK_FAILURE_THRESHOLD", "3")),
        success_threshold=int(os.getenv("HEALTH_CHECK_SUCCESS_THRESHOLD", "2"))
    )
    
    # Circuit breaker configuration
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")),
        recovery_timeout=int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60")),
        success_threshold=int(os.getenv("CIRCUIT_BREAKER_SUCCESS_THRESHOLD", "3"))
    )
    
    # Load balancer configuration
    algorithm = os.getenv("LOAD_BALANCER_ALGORITHM", "priority_with_fallback")
    load_balancer_config = LoadBalancerConfig(
        algorithm=LoadBalancerAlgorithm(algorithm),
        request_timeout=int(os.getenv("LOAD_BALANCER_TIMEOUT", "30")),
        max_retries=int(os.getenv("LOAD_BALANCER_MAX_RETRIES", "3"))
    )
    
    return ServiceDiscovery(health_config, circuit_breaker_config, load_balancer_config)


def load_service_config_from_env() -> Dict[str, List[Dict[str, Any]]]:
    """Load service configuration from environment variables"""
    
    config = {
        "azure_openai": [],
        "azure_apim": []
    }
    
    # Primary Azure OpenAI endpoint
    if os.getenv("AZURE_OPENAI_ENDPOINT"):
        config["azure_openai"].append({
            "name": "primary",
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
            "priority": 1,
            "health_check_url": "/v1/models"
        })
    
    # Secondary Azure OpenAI endpoint (if configured)
    if os.getenv("AZURE_OPENAI_SECONDARY_ENDPOINT"):
        config["azure_openai"].append({
            "name": "secondary",
            "endpoint": os.getenv("AZURE_OPENAI_SECONDARY_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_SECONDARY_KEY", ""),
            "priority": 2,
            "health_check_url": "/v1/models"
        })
    
    # Azure APIM endpoint
    if os.getenv("AZURE_APIM_OPENAI_ENDPOINT"):
        config["azure_apim"].append({
            "name": "apim_gateway",
            "endpoint": os.getenv("AZURE_APIM_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY", ""),
            "priority": 1,
            "health_check_url": "/health"
        })
    
    return config