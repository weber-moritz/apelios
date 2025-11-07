# /src/apelios/steamdeck/controller.py

from bitsteam.deck import SteamDeck

class SteamdeckInputs:
    
    def __init__(self, sensitivity: float) -> None:
        """
        Initialize a SteamdeckInputs helper.

        Parameters:
            sensitivity (float): scaling factor applied to raw gyro values returned by the SteamDeck.

        Notes:
            Call start() to initialize the SteamDeck connection.
        """
        
        self.sensitivity = sensitivity
        
        self.deck = SteamDeck()
        self.angle = [0.0, 0.0]
        
    
    def getAngle(self):
        """
        Returns the absolute gyro angles, scaled by sensitivity
        """
        gyro_pitch = self.deck.imu.get('pitch', 0) * self.sensitivity
        gyro_yaw = self.deck.imu.get('yaw', 0) * self.sensitivity
        
        # Accumulate angles
        self.angle[0] += gyro_pitch
        self.angle[1] += gyro_yaw
        
        return tuple(self.angle)
    
    def getAngleAcceleration(self):
        """
        Returns the delta gyro angles, scaled by sensitivity
        """
        gyro_pitch = self.deck.imu.get('pitch', 0) * self.sensitivity
        gyro_yaw = self.deck.imu.get('yaw', 0) * self.sensitivity
        
        return (gyro_pitch, gyro_yaw)
    
    def printImu(self):
        """Print raw IMU rates"""
        imu = self.deck.get_imu_rates()
        
        # DEBUG: See what get_imu_rates() actually returns
        # print(f"\nDEBUG - get_imu_rates() returns: {imu}")
        
        pitch_rate = imu.get('pitch', 0)
        yaw_rate = imu.get('yaw', 0)
        roll_rate = imu.get('roll', 0)
        
        print(
            f"\rPitch: {pitch_rate:8.2f}°/frame | "
            f"Yaw: {yaw_rate:8.2f}°/frame | "
            f"Roll: {roll_rate:8.2f}°/frame",
            end="",
            flush=True
        )
        
        
    def start(self):
        self.deck.start()