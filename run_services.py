import subprocess
import time

services = [
    ("auth_service/auth.py", 5001),
    ("book_service/book.py", 5002),
    ("borrow_service/borrow.py", 5003)
]

processes = []

if __name__ == '__main__':
    for service, port in services:
        print(f"starting {service} on port {port}...")
        process = subprocess.Popen(["python", service])
        processes.append(process)
        time.sleep(2)

    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\nclose all services...")
        for process in processes:
            process.terminate()