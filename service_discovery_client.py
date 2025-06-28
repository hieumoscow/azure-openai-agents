"""
Service Discovery Client Adapter for Azure OpenAI

This module provides an adapter that integrates the service discovery functionality
with the Azure OpenAI client, enabling automatic endpoint selection, health monitoring,
and failover capabilities.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
from openai import AsyncAzureOpenAI
from service_discovery import (
    ServiceDiscovery, 
    EndpointConfig, 
    create_service_discovery_from_env,
    load_service_config_from_env
)

logger = logging.getLogger(__name__)


class ServiceDiscoveryOpenAIClient:
    """
    A wrapper around AsyncAzureOpenAI that uses service discovery for endpoint management.
    Provides automatic failover, load balancing, and health monitoring.
    """
    
    def __init__(self, service_discovery: ServiceDiscovery, service_name: str = "azure_openai"):
        self.service_discovery = service_discovery
        self.service_name = service_name
        self._current_client: Optional[AsyncAzureOpenAI] = None
        self._current_endpoint: Optional[EndpointConfig] = None
    
    async def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create an OpenAI client using service discovery"""
        
        # Get the best available endpoint
        endpoint = await self.service_discovery.get_endpoint(self.service_name)
        
        if not endpoint:
            raise RuntimeError(f"No healthy endpoints available for service: {self.service_name}")
        
        # Check if we need to create a new client (endpoint changed)
        if not self._current_client or self._current_endpoint != endpoint:
            logger.info(f"Creating new OpenAI client for endpoint: {endpoint.name}")
            
            # Release the previous endpoint if any
            if self._current_endpoint:
                self.service_discovery.release_endpoint(self._current_endpoint)
            
            # Create new client with the selected endpoint
            self._current_client = AsyncAzureOpenAI(
                api_key=endpoint.api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=endpoint.endpoint,
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                timeout=endpoint.timeout
            )
            
            self._current_endpoint = endpoint
        
        return self._current_client
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._current_endpoint:
            self.service_discovery.release_endpoint(self._current_endpoint)
    
    def __getattr__(self, name):
        """Delegate attribute access to the underlying OpenAI client"""
        async def async_method(*args, **kwargs):
            client = await self._get_client()
            method = getattr(client, name)
            
            try:
                # Execute the method with retry logic
                return await self._execute_with_retry(method, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error calling {name} on endpoint {self._current_endpoint.name if self._current_endpoint else 'unknown'}: {e}")
                # Force client recreation on next call
                self._current_client = None
                if self._current_endpoint:
                    self.service_discovery.release_endpoint(self._current_endpoint)
                    self._current_endpoint = None
                raise
        
        # For sync methods, return them directly
        if hasattr(AsyncAzureOpenAI, name):
            return async_method
        
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    async def _execute_with_retry(self, method, *args, **kwargs):
        """Execute a method with retry logic on failures"""
        max_retries = 3
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                return await method(*args, **kwargs)
            except Exception as e:
                retry_count += 1
                
                if retry_count > max_retries:
                    raise
                
                logger.warning(f"Attempt {retry_count} failed for {method.__name__}: {e}")
                
                # Force endpoint reselection on retry
                self._current_client = None
                if self._current_endpoint:
                    self.service_discovery.release_endpoint(self._current_endpoint)
                    self._current_endpoint = None
                
                # Exponential backoff
                await asyncio.sleep(2 ** (retry_count - 1))
    
    def get_current_endpoint_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently selected endpoint"""
        if not self._current_endpoint:
            return None
        
        return {
            "name": self._current_endpoint.name,
            "endpoint": self._current_endpoint.endpoint,
            "priority": self._current_endpoint.priority,
            "enabled": self._current_endpoint.enabled,
            "status": self.service_discovery.health_monitor.get_endpoint_metrics(
                self._current_endpoint.name
            ).status.value if self.service_discovery.health_monitor.get_endpoint_metrics(
                self._current_endpoint.name
            ) else "unknown"
        }


class ServiceDiscoveryAPIMClient(ServiceDiscoveryOpenAIClient):
    """
    Service discovery client specifically for Azure API Management endpoints
    """
    
    def __init__(self, service_discovery: ServiceDiscovery):
        super().__init__(service_discovery, "azure_apim")
    
    async def _get_client(self) -> AsyncAzureOpenAI:
        """Get or create an APIM OpenAI client using service discovery"""
        
        # Get the best available APIM endpoint
        endpoint = await self.service_discovery.get_endpoint(self.service_name)
        
        if not endpoint:
            raise RuntimeError(f"No healthy APIM endpoints available")
        
        # Check if we need to create a new client (endpoint changed)
        if not self._current_client or self._current_endpoint != endpoint:
            logger.info(f"Creating new APIM OpenAI client for endpoint: {endpoint.name}")
            
            # Release the previous endpoint if any
            if self._current_endpoint:
                self.service_discovery.release_endpoint(self._current_endpoint)
            
            # Create new APIM client with the selected endpoint
            self._current_client = AsyncAzureOpenAI(
                default_headers={"Ocp-Apim-Subscription-Key": endpoint.api_key},
                api_key=endpoint.api_key,
                api_version=os.getenv("AZURE_APIM_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=endpoint.endpoint,
                timeout=endpoint.timeout
            )
            
            self._current_endpoint = endpoint
        
        return self._current_client


async def create_service_discovery_client(service_name: str = "azure_openai") -> ServiceDiscoveryOpenAIClient:
    """
    Factory function to create a service discovery-enabled OpenAI client
    """
    
    # Check if service discovery is enabled
    if not os.getenv("SERVICE_DISCOVERY_ENABLED", "false").lower() == "true":
        logger.info("Service discovery disabled, using traditional client")
        return None
    
    # Create service discovery instance
    service_discovery = create_service_discovery_from_env()
    
    # Load service configuration
    service_config = load_service_config_from_env()
    
    # Initialize service discovery
    await service_discovery.initialize(service_config)
    
    # Create appropriate client based on service name
    if service_name == "azure_apim":
        return ServiceDiscoveryAPIMClient(service_discovery)
    else:
        return ServiceDiscoveryOpenAIClient(service_discovery, service_name)


async def create_fallback_client() -> AsyncAzureOpenAI:
    """
    Create a fallback client using the traditional environment variable approach
    This is used when service discovery is disabled or fails
    """
    
    # Try APIM client first if configured
    if os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY"):
        logger.info("Creating fallback APIM client")
        return AsyncAzureOpenAI(
            default_headers={"Ocp-Apim-Subscription-Key": os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY")},
            api_key=os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY"),
            api_version=os.getenv("AZURE_APIM_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_APIM_OPENAI_ENDPOINT")
        )
    
    # Fall back to direct Azure OpenAI client
    elif os.getenv("AZURE_OPENAI_API_KEY"):
        logger.info("Creating fallback Azure OpenAI client")
        return AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )
    
    else:
        raise RuntimeError("No Azure OpenAI configuration found")


# Health check utilities

async def check_service_health(service_name: str) -> Dict[str, Any]:
    """Check the health of all endpoints for a specific service"""
    
    service_discovery = create_service_discovery_from_env()
    service_config = load_service_config_from_env()
    
    await service_discovery.initialize(service_config)
    
    try:
        status = service_discovery.get_service_status(service_name)
        return status
    finally:
        await service_discovery.shutdown()


async def test_endpoint_connectivity(service_name: str, endpoint_name: str) -> Dict[str, Any]:
    """Test connectivity to a specific endpoint"""
    
    service_discovery = create_service_discovery_from_env()
    service_config = load_service_config_from_env()
    
    await service_discovery.initialize(service_config)
    
    try:
        # Wait a moment for initial health checks
        await asyncio.sleep(2)
        
        endpoints = service_discovery.services.get(service_name, [])
        endpoint = next((ep for ep in endpoints if ep.name == endpoint_name), None)
        
        if not endpoint:
            return {"error": f"Endpoint {endpoint_name} not found in service {service_name}"}
        
        metrics = service_discovery.health_monitor.get_endpoint_metrics(endpoint_name)
        
        return {
            "endpoint_name": endpoint_name,
            "endpoint_url": endpoint.endpoint,
            "status": metrics.status.value if metrics else "unknown",
            "last_check": metrics.last_check.isoformat() if metrics and metrics.last_check else None,
            "response_time": metrics.response_time if metrics else 0,
            "last_error": metrics.last_error if metrics else None
        }
    
    finally:
        await service_discovery.shutdown()


# CLI utilities for debugging

if __name__ == "__main__":
    import sys
    import json
    
    async def main():
        if len(sys.argv) < 2:
            print("Usage: python service_discovery_client.py <command> [args]")
            print("Commands:")
            print("  health-status [service_name]")
            print("  test-endpoint <service_name> <endpoint_name>")
            print("  show-config")
            return
        
        command = sys.argv[1]
        
        if command == "health-status":
            service_name = sys.argv[2] if len(sys.argv) > 2 else "azure_openai"
            status = await check_service_health(service_name)
            print(json.dumps(status, indent=2))
        
        elif command == "test-endpoint":
            if len(sys.argv) < 4:
                print("Usage: test-endpoint <service_name> <endpoint_name>")
                return
            
            service_name = sys.argv[2]
            endpoint_name = sys.argv[3]
            result = await test_endpoint_connectivity(service_name, endpoint_name)
            print(json.dumps(result, indent=2))
        
        elif command == "show-config":
            config = load_service_config_from_env()
            print(json.dumps(config, indent=2))
        
        else:
            print(f"Unknown command: {command}")
    
    asyncio.run(main())