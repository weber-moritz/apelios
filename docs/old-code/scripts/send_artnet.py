import asyncio
import logging
import time
from aioartnet import ArtNetClient, ArtNetUniverse

# --- Configuration ---
# ⚠️ Set your IP and Broadcast IP here
YOUR_IP = "192.168.8.1"
YOUR_BROADCAST_IP = "192.168.8.255"

# Configure which universe you want to send to (input to Art-Net)
# We will send on Net 0, Sub-Net 0, Universe 1
UNIVERSE_TO_SEND = 1
# ---------------------

# Set up logging to see what's happening
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")


async def send_dmx_changes(universe: ArtNetUniverse):
    """This task just fades channel 1 up and down on a universe."""
    log.info(f"Starting DMX sender task for {universe}...")
    
    # Create a 512-byte array for our DMX data
    dmx_data = bytearray(512)
    value = 0
    direction = 1

    try:
        while True:
            # Modify channel 1 (index 0)
            dmx_data[0] = value
            
            # Set the DMX data for the universe
            # This automatically sends it to all subscribers
            universe.set_dmx(bytes(dmx_data))
            
            # Update the value for the next loop
            value += direction
            if value >= 255:
                value = 255
                direction = -1
            if value <= 0:
                value = 0
                direction = 1
            
            # Run this loop at ~25 Hz
            await asyncio.sleep(0.025) 
    except asyncio.CancelledError:
        log.info("DMX sender stopped.")


async def main():
    """The main application function."""
    client = ArtNetClient()
    main_tasks = []
    
    client.unicast_ip = YOUR_IP
    client.broadcast_ip = YOUR_BROADCAST_IP

    try:
        # Connect to the network
        await client.connect()
        log.info("Aioartnet client connected successfully!")
        log.info(f"Listening on: {client.unicast_ip}")

        # --- Configure Our Port ---
        
        # We want to *send* DMX to universe 1
        u_send = client.set_port_config(
            universe=UNIVERSE_TO_SEND,
            is_input=True   # 'input' to the network, so 'output' from us
        )
        
        # Start the background task
        dmx_send_task = asyncio.create_task(send_dmx_changes(u_send))
        main_tasks = [dmx_send_task]

        log.info("Running application. Press Ctrl+C to stop.")
        
        # Wait forever (or until Ctrl+C)
        await asyncio.Event().wait()

    except asyncio.CancelledError:
        log.info("Main task cancelled. Shutting down.")
    except Exception as e:
        log.error(f"An error occurred: {e}")
    finally:
        # Stop our background tasks
        for task in main_tasks:
            if not task.done():
                task.cancel()
        
        # Close the network connection
        if client.protocol and client.protocol.transport:
            client.protocol.transport.close()
            
        log.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Received Ctrl+C, stopping.")

