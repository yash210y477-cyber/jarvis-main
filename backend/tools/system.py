import platform
import socket
import time

import psutil


BOOT_TIME = time.time() - psutil.boot_time()


def system_status():

    memory = psutil.virtual_memory()

    disk = psutil.disk_usage("/")

    battery = psutil.sensors_battery()

    cpu = psutil.cpu_percent(interval=0.5)

    return {
        "success": True,

        "cpu": round(cpu),

        "ram": round(memory.percent),

        "storage": round(disk.percent),

        "battery": (
            round(battery.percent)
            if battery
            else None
        ),

        "hostname": socket.gethostname(),

        "os": platform.system(),

        "os_version": platform.version(),

        "processor": platform.processor(),

        "uptime": round(BOOT_TIME)
    }