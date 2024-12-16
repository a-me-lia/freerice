import subprocess

import time

from config import USE_VPN

def switch_vpn_server(times):
    if not USE_VPN:
        return
    """
    Switches to a random NordVPN server using the NordVPN CLI.
    """
    try:


        if times % 6 == 0:
            disconnect_vpn()

        if times % 6 == 1:
            subprocess.run(
                ["nordvpn", "-c", "-n", "Slovenia #16"]
            )
        if times % 6 == 2:
            subprocess.run(
                ["nordvpn", "-c", "-n", "Slovenia #19"]
            )
        if times % 6 == 3:
            disconnect_vpn()
        if times % 6 == 4:
            subprocess.run(
                ["nordvpn", "-c", "-n", "Slovenia #15"]
            )
        if times % 6 == 5:
            subprocess.run(
                ["nordvpn", "-c", "-n", "Slovenia #14"]
            )



        print(f"Connected new IP.")
    except Exception as e:
        print(f"Error while switching VPN server: {e}")

def disconnect_vpn():
    if not USE_VPN:
        return
    """
    Disconnects the current VPN connection using NordVPN CLI.
    """
    try:
        subprocess.run(
            ["nordvpn", "--disconnect"]
        )
        print("Disconnected from VPN.")
    except Exception as e:
        print(f"Error while disconnecting VPN: {e}")
