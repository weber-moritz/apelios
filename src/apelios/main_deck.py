# apelios.main_deck.py 
# runs on the deck, sends artnet to grandma (or other) and recieves video stream from apelios.main_stream.py


import logging
import asyncio
import sys
from apelios.artnet import ArtNetController
from apelios.steamdeck import SteamdeckInputs
from apelios.video_receiver.receiver import run_receiver


# Logging EINMAL hier konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('apelios.log'),  # Log-Datei im Projekt-Root
        logging.StreamHandler()               # Console output
    ]
)

log = logging.getLogger(__name__)


async def main():
    log.info("Starting Apelios...")
    
    # Art-Net Controller erstellen
    artnet = ArtNetController(
        # source_ip="192.168.8.1",
        # target_ip="192.168.8.144",
        source_ip="10.0.0.102",
        target_ip="10.0.0.12",
        universe=2
    )
    
    
    # Verbinden
    await artnet.connect()
    
    deck = SteamdeckInputs(5.0)
    deck.start()
    
    
    # Output starten (als Task - läuft parallel)
    output_task = asyncio.create_task(artnet.start())
    # Start the video receiver as an asyncio task (non-blocking)
    # Use display=False by default to avoid opening GUI on headless devices
    
    # Video receiver configuration
    video_host = "192.168.8.144" #"127.0.0.1"
    video_port = 9999
    video_display = True
    video_save_frames = False
    video_enable_detection = True
    video_detection_method = "hog"
    video_confidence_threshold = 0.5
    
    video_task = asyncio.create_task(run_receiver(
        video_host, 
        video_port,
        video_display,
        video_save_frames,
        video_enable_detection,
        video_detection_method,
        video_confidence_threshold))

    # Minimal terminal key listener: read one char in executor and set event
    stop_event = asyncio.Event()

    async def key_wait(ev: asyncio.Event):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sys.stdin.read, 1)
        ev.set()

    key_task = asyncio.create_task(key_wait(stop_event))
    
    # Main loop
    try:
        angles = [100.0,100.0]
        while True:
            if stop_event.is_set():
                log.info("Key pressed, exiting main loop")
                break
            # Hier später: Steam Deck Input lesen
            angles[0] += deck.getAngleAcceleration()[0]
            angles[1] += deck.getAngleAcceleration()[1]

            print(f"\rAngles: pan={angles[0]:4.3f}°, tilt={angles[1]:4.3f}°", end="", flush=True)
            
            artnet.set_channel(1, int(angles[0]))
            artnet.set_channel(2, int(angles[1]))
            
            await asyncio.sleep(0.01)
            
            # deck.printImu()
    
    except KeyboardInterrupt:
        log.info("Stopping...")
    
    finally:
        # Cancel video receiver task and wait for it to finish
        try:
            if video_task and not video_task.done():
                video_task.cancel()
                try:
                    await video_task
                except asyncio.CancelledError:
                    log.info("Video receiver task cancelled")
        except NameError:
            pass

        await artnet.close()

        # cancel key listener if still running
        try:
            if key_task and not key_task.done():
                key_task.cancel()
                try:
                    await key_task
                except asyncio.CancelledError:
                    pass
        except NameError:
            pass


if __name__ == "__main__":
    asyncio.run(main())