import socket
from datetime import datetime
import concurrent.futures

def scan_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, port))
        if result == 0:
            return port
        else:
            return None
    except socket.error:
        return None

def scan_ports(ip):
    print(f"Scanning open ports on {ip}...\n")
    print(f"Scanning started at {datetime.now()}")

    open_ports = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(scan_port, ip, port): port for port in range(1, 65536)}
        
        for future in concurrent.futures.as_completed(futures):
            port = future.result()
            if port:
                open_ports.append(port)
                print(f"Port {port} is OPEN")

    if not open_ports:
        print("No open ports found.")
    print(f"\nScanning finished at {datetime.now()}")

def main():
    ip = input("Enter the IP address to scan: ")
    try:
        scan_ports(ip)

    except ValueError:
        print("Invalid input. Please enter a valid IP address.")

if __name__ == "__main__":
    main()

                                