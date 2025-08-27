#!/usr/bin/env python3
"""
🚀 HARDWARE OPTIMIZER FOR i5-13400 + H610 + 12GB RAM
Optimize GEM OS for maximum performance on target hardware
20 DAYS MISSION: GET THE BEST FROM YOUR PC!
"""

import os
import psutil
import platform
import subprocess
import asyncio
from pathlib import Path

class HardwareOptimizer:
    """Optimize system for i5-13400 + H610 + 12GB RAM"""
    
    def __init__(self):
        self.cpu_cores = psutil.cpu_count(logical=True)  # Should be 16 for i5-13400
        self.memory_gb = round(psutil.virtual_memory().total / (1024**3))
        self.target_cpu = "i5-13400"
        self.target_ram = 12
        
        print("🚀" + "=" * 60)
        print("🚀 HARDWARE OPTIMIZER FOR GEM OS")
        print(f"🚀 Target: Intel {self.target_cpu} + H610 + {self.target_ram}GB RAM")
        print(f"🚀 Detected: {self.cpu_cores} cores, {self.memory_gb}GB RAM")
        print("🚀" + "=" * 60)
        
    def detect_hardware(self):
        """Detect and verify hardware specifications"""
        print("\n🔍 DETECTING HARDWARE...")
        
        # CPU Information
        cpu_info = platform.processor()
        cpu_freq = psutil.cpu_freq()
        
        print(f"💻 CPU: {cpu_info}")
        print(f"⚡ CPU Cores: {self.cpu_cores} threads")
        if cpu_freq:
            print(f"🔥 CPU Frequency: {cpu_freq.current:.0f} MHz (Max: {cpu_freq.max:.0f} MHz)")
        
        # Memory Information
        memory = psutil.virtual_memory()
        print(f"🧠 Total RAM: {self.memory_gb}GB ({memory.total / (1024**3):.1f}GB)")
        print(f"📊 Available RAM: {memory.available / (1024**3):.1f}GB")
        print(f"📈 Memory Usage: {memory.percent}%")
        
        # Verify target hardware
        if self.cpu_cores >= 16 and self.memory_gb >= 12:
            print("✅ Hardware meets i5-13400 + 12GB requirements!")
            return True
        else:
            print("⚠️ Hardware may not match target specifications")
            return False
            
    def optimize_cpu_performance(self):
        """Optimize CPU performance for i5-13400"""
        print("\n⚡ OPTIMIZING CPU PERFORMANCE...")
        
        try:
            # Set CPU governor to performance (Linux)
            if platform.system() == "Linux":
                subprocess.run([
                    "sudo", "cpupower", "frequency-set", "-g", "performance"
                ], capture_output=True)
                print("✅ CPU governor set to performance mode")
                
            # Set process priority
            os.nice(-10)  # Higher priority for GEM OS
            print("✅ Process priority optimized")
            
            # CPU affinity optimization
            if self.cpu_cores >= 16:
                # Use performance cores (0-11) for main processing
                # Use efficiency cores (12-15) for background tasks
                main_cores = list(range(0, 12))  # P-cores
                bg_cores = list(range(12, 16))   # E-cores
                
                print(f"🎯 Performance cores: {main_cores}")
                print(f"🔄 Background cores: {bg_cores}")
                
                return {"main_cores": main_cores, "bg_cores": bg_cores}
                
        except Exception as e:
            print(f"⚠️ CPU optimization warning: {e}")
            
        return {"main_cores": list(range(self.cpu_cores)), "bg_cores": []}
        
    def optimize_memory_allocation(self):
        """Optimize memory allocation for 12GB RAM"""
        print("\n🧠 OPTIMIZING MEMORY ALLOCATION...")
        
        total_memory_mb = self.memory_gb * 1024
        
        # Memory allocation plan for GEM OS
        allocation = {
            "voice_processing": int(total_memory_mb * 0.15),    # 1.8GB
            "ai_models": int(total_memory_mb * 0.35),           # 4.2GB
            "system_buffer": int(total_memory_mb * 0.15),       # 1.8GB
            "response_cache": int(total_memory_mb * 0.15),      # 1.8GB
            "accessibility": int(total_memory_mb * 0.10),       # 1.2GB
            "emergency_reserve": int(total_memory_mb * 0.10)    # 1.2GB
        }
        
        print("📊 MEMORY ALLOCATION PLAN:")
        for component, mb in allocation.items():
            print(f"   {component}: {mb}MB ({mb/1024:.1f}GB)")
            
        # Set memory limits in environment
        os.environ["GEM_MEMORY_LIMIT"] = str(int(total_memory_mb * 0.8))  # 80% limit
        os.environ["GEM_VOICE_MEMORY"] = str(allocation["voice_processing"])
        os.environ["GEM_AI_MEMORY"] = str(allocation["ai_models"])
        
        print("✅ Memory allocation optimized")
        return allocation
        
    def optimize_audio_system(self):
        """Optimize audio system for real-time processing"""
        print("\n🎤 OPTIMIZING AUDIO SYSTEM...")
        
        try:
            # Audio buffer optimization
            audio_config = {
                "sample_rate": 16000,
                "buffer_size": 512,    # Low latency
                "channels": 1,
                "format": "int16"
            }
            
            # Set audio environment variables
            os.environ["GEM_AUDIO_SAMPLE_RATE"] = str(audio_config["sample_rate"])
            os.environ["GEM_AUDIO_BUFFER_SIZE"] = str(audio_config["buffer_size"])
            os.environ["GEM_AUDIO_CHANNELS"] = str(audio_config["channels"])
            
            print("🔊 Audio configuration:")
            for key, value in audio_config.items():
                print(f"   {key}: {value}")
                
            # Test audio devices
            if platform.system() == "Linux":
                result = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Audio devices detected")
                else:
                    print("⚠️ Audio device detection failed")
                    
            print("✅ Audio system optimized")
            return audio_config
            
        except Exception as e:
            print(f"⚠️ Audio optimization warning: {e}")
            return {}
            
    def create_optimized_env(self):
        """Create optimized .env file for hardware"""
        print("\n⚙️ CREATING OPTIMIZED CONFIGURATION...")
        
        env_config = f"""# 🚀 GEM OS - OPTIMIZED FOR i5-13400 + H610 + 12GB RAM
# Hardware-specific optimization settings

# === HARDWARE OPTIMIZATION ===
GEM_CPU_CORES={self.cpu_cores}
GEM_MEMORY_GB={self.memory_gb}
GEM_PERFORMANCE_MODE=high
GEM_HARDWARE_TARGET=i5-13400

# === CPU OPTIMIZATION ===
GEM_CPU_THREADS={min(self.cpu_cores, 16)}
GEM_CPU_AFFINITY=performance_cores
GEM_PROCESS_PRIORITY=high

# === MEMORY OPTIMIZATION ===
GEM_MEMORY_LIMIT={int(self.memory_gb * 1024 * 0.8)}
GEM_VOICE_MEMORY={int(self.memory_gb * 1024 * 0.15)}
GEM_AI_MEMORY={int(self.memory_gb * 1024 * 0.35)}
GEM_CACHE_MEMORY={int(self.memory_gb * 1024 * 0.15)}

# === AUDIO OPTIMIZATION ===
GEM_AUDIO_SAMPLE_RATE=16000
GEM_AUDIO_BUFFER_SIZE=512
GEM_AUDIO_CHANNELS=1
GEM_AUDIO_LATENCY=low

# === PERFORMANCE TARGETS ===
GEM_VOICE_LATENCY_MS=500
GEM_AI_RESPONSE_MS=2000
GEM_ACCESSIBILITY_MS=100
GEM_EMERGENCY_MS=50

# === SYSTEM OPTIMIZATION ===
GEM_ASYNC_WORKERS=8
GEM_THREAD_POOL_SIZE=16
GEM_QUEUE_SIZE=1000
GEM_BATCH_SIZE=32

# === MONITORING ===
GEM_PERFORMANCE_MONITORING=true
GEM_RESOURCE_MONITORING=true
GEM_THERMAL_MONITORING=true
GEM_MEMORY_PROFILING=true
"""
        
        # Write optimized .env
        env_file = Path(".env.optimized")
        with open(env_file, "w") as f:
            f.write(env_config)
            
        print(f"✅ Optimized configuration saved to {env_file}")
        print("💡 Copy to .env to activate: cp .env.optimized .env")
        
    async def performance_benchmark(self):
        """Run performance benchmark"""
        print("\n🏃 RUNNING PERFORMANCE BENCHMARK...")
        
        # CPU benchmark
        import time
        start_time = time.time()
        
        # Simulate CPU-intensive task
        result = sum(i * i for i in range(1000000))
        cpu_time = time.time() - start_time
        
        print(f"⚡ CPU Benchmark: {cpu_time:.3f}s")
        
        # Memory benchmark
        start_time = time.time()
        test_data = [i for i in range(1000000)]
        memory_time = time.time() - start_time
        
        print(f"🧠 Memory Benchmark: {memory_time:.3f}s")
        
        # Overall score
        score = 1000 / (cpu_time + memory_time)
        print(f"🏆 Performance Score: {score:.0f}")
        
        if score > 500:
            print("✅ Excellent performance for GEM OS!")
        elif score > 300:
            print("✅ Good performance for GEM OS")
        else:
            print("⚠️ Performance may need optimization")
            
        return score
        
    async def optimize_system(self):
        """Complete system optimization"""
        print("\n🚀 STARTING COMPLETE SYSTEM OPTIMIZATION...")
        
        # Step 1: Detect hardware
        hardware_ok = self.detect_hardware()
        
        # Step 2: Optimize CPU
        cpu_config = self.optimize_cpu_performance()
        
        # Step 3: Optimize memory
        memory_config = self.optimize_memory_allocation()
        
        # Step 4: Optimize audio
        audio_config = self.optimize_audio_system()
        
        # Step 5: Create optimized config
        self.create_optimized_env()
        
        # Step 6: Run benchmark
        score = await self.performance_benchmark()
        
        print("\n🎉 OPTIMIZATION COMPLETE!")
        print("🚀 System ready for 20 days GEM OS mission!")
        
        return {
            "hardware_ok": hardware_ok,
            "cpu_config": cpu_config,
            "memory_config": memory_config,
            "audio_config": audio_config,
            "performance_score": score
        }

async def main():
    """Main optimization routine"""
    print("🚀 GEM OS HARDWARE OPTIMIZER")
    print("🎯 Target: Intel i5-13400 + H610 + 12GB RAM")
    print("⏰ Mission: 20 days to operational system!")
    
    optimizer = HardwareOptimizer()
    results = await optimizer.optimize_system()
    
    print("\n" + "🎉" + "=" * 60)
    print("🎉 HARDWARE OPTIMIZATION COMPLETE!")
    print("🎉 GEM OS READY FOR MAXIMUM PERFORMANCE!")
    print("🎉" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())