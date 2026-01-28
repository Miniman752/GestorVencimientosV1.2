import os
import psutil

ports = [8000, 8550]

print("Scanning for blocking processes...")
for proc in psutil.process_iter(['pid', 'name']):
    try:
        for con in proc.connections():
            if con.laddr.port in ports:
                print(f"Killing {proc.info['name']} (PID {proc.info['pid']}) on port {con.laddr.port}")
                proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
print("Ports cleared.")
