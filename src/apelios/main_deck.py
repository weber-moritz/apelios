# apelios.main_deck.py 
# runs on the deck, sends artnet to grandma (or other) and recieves video stream from apelios.main_stream.py


import logging
import asyncio
from apelios.artnet import ArtNetController
from apelios.steamdeck import SteamdeckInputs

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
        source_ip="192.168.8.1",
        target_ip="192.168.8.144",
        universe=1
    )
    
    
    # Verbinden
    await artnet.connect()
    
    deck = SteamdeckInputs(5.0)
    deck.start()
    
    
    # Output starten (als Task - läuft parallel)
    output_task = asyncio.create_task(artnet.start())
    
    
    # Main loop
    try:
        angles = [100.0,100.0]
        while True:
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
        await artnet.close()


if __name__ == "__main__":
    asyncio.run(main())