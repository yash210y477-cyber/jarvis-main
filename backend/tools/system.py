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

    cpu = round(cpu)
    ram = round(memory.percent)
    storage = round(disk.percent)

    message = f"CPU {cpu}% · RAM {ram}% · Storage {storage}%"

    if battery:

        message += f" · Battery {round(battery.percent)}%"

    return {
        "success": True,

        "message": message,

        "cpu": cpu,

        "ram": ram,

        "storage": storage,

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