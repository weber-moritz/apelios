import logging
import asyncio
from apelios.artnet import ArtNetController

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
    
    # Output starten (als Task - läuft parallel)
    output_task = asyncio.create_task(artnet.start())
    
    # Hauptloop
    try:
        direction = 1
        value = 0
        while True:
            # Hier später: Steam Deck Input lesen
            value += direction
            if value >= 255:
                value = 255
                direction = -1
            if value <= 0:
                value = 0
                direction = 1
                
            artnet.set_channel(1, value)
            await asyncio.sleep(0.01)
    
    except KeyboardInterrupt:
        log.info("Stopping...")
    
    finally:
        await artnet.close()


if __name__ == "__main__":
    asyncio.run(main())