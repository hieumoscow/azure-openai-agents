#!/usr/bin/env python3
"""
Service Discovery Demo

This script demonstrates the service discovery functionality in action.
Run this to see how the system handles endpoint selection, health monitoring,
and failover scenarios.
"""

import asyncio
import os
import time
from service_discovery import ServiceDiscovery, HealthCheckConfig, LoadBalancerConfig, LoadBalancerAlgorithm

async def demo_service_discovery():
    """Demonstrate service discovery capabilities"""
    
    print("🌟 Azure OpenAI Service Discovery Demo")
    print("=" * 50)
    
    # Configure service discovery with shorter intervals for demo
    health_config = HealthCheckConfig(
        interval=10,  # Check every 10 seconds
        timeout=5,    # 5 second timeout
        retries=2,    # 2 retry attempts
        failure_threshold=2,  # Mark unhealthy after 2 failures
        success_threshold=1   # Mark healthy after 1 success
    )
    
    lb_config = LoadBalancerConfig(
        algorithm=LoadBalancerAlgorithm.PRIORITY_WITH_FALLBACK,
        max_retries=3
    )
    
    service_discovery = ServiceDiscovery(health_config, None, lb_config)
    
    # Demo configuration with multiple endpoints
    demo_config = {
        "azure_openai": [
            {
                "name": "primary_east",
                "endpoint": "https://httpbin.org",  # Using httpbin for demo
                "api_key": "demo_key_east",
                "priority": 1,
                "health_check_url": "/status/200",  # This will be healthy
                "metadata": {"region": "East US", "tier": "standard"}
            },
            {
                "name": "secondary_west",
                "endpoint": "https://httpbin.org",
                "api_key": "demo_key_west", 
                "priority": 2,
                "health_check_url": "/status/500",  # This will be unhealthy
                "metadata": {"region": "West US", "tier": "standard"}
            },
            {
                "name": "backup_europe",
                "endpoint": "https://httpbin.org",
                "api_key": "demo_key_europe",
                "priority": 3,
                "health_check_url": "/status/200",  # This will be healthy
                "metadata": {"region": "Europe West", "tier": "basic"}
            }
        ]
    }
    
    try:
        print("🚀 Initializing service discovery...")
        await service_discovery.initialize(demo_config)
        print("✅ Service discovery initialized with 3 endpoints")
        
        print("\n⏳ Waiting for initial health checks...")
        await asyncio.sleep(8)  # Wait for health checks
        
        print("\n📊 Service Status:")
        status = service_discovery.get_service_status("azure_openai")
        print(f"Total endpoints: {status['total_endpoints']}")
        print(f"Healthy endpoints: {status['healthy_endpoints']}")
        print(f"Unhealthy endpoints: {status['unhealthy_endpoints']}")
        
        print("\n🔍 Endpoint Details:")
        for endpoint in status['endpoints']:
            health_emoji = "🟢" if endpoint['status'] == 'healthy' else "🔴" if endpoint['status'] == 'unhealthy' else "🟡"
            print(f"  {health_emoji} {endpoint['name']} (priority {endpoint['priority']}) - {endpoint['status']}")
            if endpoint['last_check']:
                print(f"    Last check: {endpoint['last_check']}")
                print(f"    Response time: {endpoint['response_time']:.3f}s")
                print(f"    Success rate: {endpoint['success_rate']:.1f}%")
        
        print("\n🎯 Testing Endpoint Selection:")
        for i in range(5):
            endpoint = await service_discovery.get_endpoint("azure_openai")
            if endpoint:
                print(f"  Attempt {i+1}: Selected '{endpoint.name}' (priority {endpoint.priority})")
                service_discovery.release_endpoint(endpoint)
            else:
                print(f"  Attempt {i+1}: No healthy endpoint available")
            await asyncio.sleep(1)
        
        print("\n🔧 Demonstrating Runtime Configuration:")
        
        # Disable primary endpoint
        print("  → Disabling primary endpoint...")
        service_discovery.disable_endpoint("azure_openai", "primary_east")
        
        await asyncio.sleep(2)
        
        # Try selecting endpoint again
        endpoint = await service_discovery.get_endpoint("azure_openai")
        if endpoint:
            print(f"  → After disabling primary: Selected '{endpoint.name}' (priority {endpoint.priority})")
            service_discovery.release_endpoint(endpoint)
        
        # Re-enable primary endpoint
        print("  → Re-enabling primary endpoint...")
        service_discovery.enable_endpoint("azure_openai", "primary_east")
        
        await asyncio.sleep(2)
        
        endpoint = await service_discovery.get_endpoint("azure_openai")
        if endpoint:
            print(f"  → After re-enabling: Selected '{endpoint.name}' (priority {endpoint.priority})")
            service_discovery.release_endpoint(endpoint)
        
        print("\n🔄 Load Balancer Algorithms Demo:")
        
        # Test different algorithms
        algorithms = [
            (LoadBalancerAlgorithm.PRIORITY, "Priority-based selection"),
            (LoadBalancerAlgorithm.ROUND_ROBIN, "Round-robin distribution"),
            (LoadBalancerAlgorithm.PRIORITY_WITH_FALLBACK, "Priority with fallback")
        ]
        
        for algorithm, description in algorithms:
            print(f"\n  🔀 Testing {description}:")
            service_discovery.load_balancer.config.algorithm = algorithm
            service_discovery.load_balancer._round_robin_index = 0  # Reset for demo
            
            selections = []
            for i in range(3):
                endpoint = await service_discovery.get_endpoint("azure_openai")
                if endpoint:
                    selections.append(endpoint.name)
                    service_discovery.release_endpoint(endpoint)
                await asyncio.sleep(0.5)
            
            print(f"    Selections: {' → '.join(selections)}")
        
        print("\n📈 Final Service Health Summary:")
        final_status = service_discovery.get_service_status("azure_openai")
        
        print(f"📊 Overall Health: {final_status['healthy_endpoints']}/{final_status['total_endpoints']} endpoints healthy")
        
        for endpoint in final_status['endpoints']:
            metrics_emoji = "📈" if endpoint['success_rate'] > 50 else "📉"
            print(f"  {metrics_emoji} {endpoint['name']}: {endpoint['success_rate']:.1f}% success rate")
        
        print("\n🎉 Demo completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✅ Multi-endpoint configuration")
        print("✅ Automatic health monitoring") 
        print("✅ Priority-based load balancing")
        print("✅ Runtime configuration changes")
        print("✅ Automatic failover handling")
        print("✅ Multiple load balancing algorithms")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n🛑 Shutting down service discovery...")
        await service_discovery.shutdown()
        print("✅ Cleanup completed")


def show_configuration_example():
    """Show example configuration"""
    print("\n📋 Example Configuration:")
    print("=" * 30)
    
    example_env = """
# Enable service discovery
SERVICE_DISCOVERY_ENABLED=true

# Primary Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://primary.openai.azure.com
AZURE_OPENAI_API_KEY=your_primary_key

# Secondary Azure OpenAI (for failover)
AZURE_OPENAI_SECONDARY_ENDPOINT=https://secondary.openai.azure.com
AZURE_OPENAI_SECONDARY_KEY=your_secondary_key

# Health monitoring
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_FAILURE_THRESHOLD=3

# Load balancing
LOAD_BALANCER_ALGORITHM=priority_with_fallback
"""
    
    print(example_env)


async def main():
    """Main demo function"""
    print("Welcome to the Azure OpenAI Service Discovery Demo!")
    print("This demo shows how the service discovery system works with multiple endpoints.")
    print("Note: This demo uses httpbin.org for demonstration purposes.\n")
    
    show_configuration_example()
    
    input("Press Enter to start the demo...")
    
    await demo_service_discovery()
    
    print("\n" + "=" * 60)
    print("🌟 Thank you for trying the Service Discovery Demo!")
    print("For more information, see docs/SERVICE_DISCOVERY.md")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())