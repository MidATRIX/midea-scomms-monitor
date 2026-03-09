# src/main.py
import asyncio
import json
import os
import time
import datetime
import paho.mqtt.client as mqtt
from database.db_handler import init_db, save_frame
from src.config import WAVESHARE_IP, WAVESHARE_PORT, KNOWN_IDS, REGISTRY_FILE, FRAME_SIZE, MQTT_IP, MQTT_PORT_NUMBER, MQTT_USER, MQTT_PASS
from src.serial.frame_buffer import FrameBuffer
from src.protocol.validator import FrameValidator
from src.decode.sensors import process_payload
from src.ha.discovery import SenvilleMQTT

async def main():
    fb = FrameBuffer()
    validator = FrameValidator()
    
    current_state = [[] for _ in range(6)]
    
    if not os.path.exists("data"):
        os.makedirs("data")
        
# --- INITIALIZE HOME ASSISTANT MQTT ---
    ha = SenvilleMQTT(MQTT_IP, MQTT_PORT_NUMBER, MQTT_USER, MQTT_PASS)
    
    print("⏳ Waiting for MQTT CONNACK handshake...")
    time.sleep(5)
    
    ha.register_all_sensors()
    
    print(f"🦅 ENGAGE | {WAVESHARE_IP}:{WAVESHARE_PORT}")

    while True:
        try:
            reader, writer = await asyncio.open_connection(WAVESHARE_IP, WAVESHARE_PORT)
            print("🔗 TCP CONNECTION ESTABLISHED")

            while True:
                try:
                    # Wait 15 seconds for data. If nothing comes, print a warning and loop.
                    data = await asyncio.wait_for(reader.read(1024), timeout=15.0)
                except asyncio.TimeoutError:
                    print("⏳ Still listening... No data from Waveshare in 15 seconds.")
                    continue
                if not data:
                    print("⚠️ CONNECTION CLOSED BY BRIDGE")
                    await asyncio.sleep(5)
                    break
                
                fb.feed(data)
                
                while True:
                    frame, noise = fb.get_frame()
                    
                    if frame is None: 
                        break
                        
                    if noise:
                        with open("data/bus_noise.log", "a") as f:
                            f.write(f"{noise.hex().upper()}\n")
                    
                    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    status_icon, seed, msg_id = validator.process(frame)
                    raw_hex = frame.hex().upper()
                    sensor_name = KNOWN_IDS.get(msg_id, f"trash_{msg_id}")
                    
                    if sensor_name.startswith("trash"): 
                        continue
                    
                    decoded_data = {}
                    if status_icon in ["✅", "🔒"]:
                        print(f"{status_icon} {raw_hex} [{ts}] [{sensor_name}]") # Comment to stop printing to terminal
                        
                        from src.decode.sensors import process_payload
                        decoded_data = process_payload(msg_id, frame)
                        
                        for key, value in decoded_data.items(): #--------------------------- Comment to disable HA MQTT
                            ha.publish_state(key, value)        #--------------------------- Comment to disable HA MQTT
                    
                    # Database Save Logic
                    if sensor_name == "IDU_CORE":
                        current_state[0] = [msg_id] + list(frame[5:17])
                    elif sensor_name == "ODU_CORE":
                        current_state[1] = [msg_id] + list(frame[5:17])
                    elif sensor_name == "ODU_50":
                        current_state[2] = [msg_id] + list(frame[5:17])
                    elif sensor_name == "ODU_51":
                        current_state[3] = [msg_id] + list(frame[5:17])
                    elif sensor_name == "ODU_52":
                        current_state[4] = [msg_id] + list(frame[5:17])
                    elif sensor_name == "ODU_53":
                        current_state[5] = [msg_id] + list(frame[5:17])
                        
                        payload_ints = [byte for section in current_state for byte in section]
                        if len(payload_ints) == 78: #-------------------------------------- Comment to disable database
                            save_frame(list(payload_ints))#-------------------------------- Comment to disable database
#                            current_state = [[] for _ in range(6)]
                    print(f"{current_state}") #------------------------------------ Comment to stop printing to terminal
                    # PRINT
#                    if status_icon == "🛰️":
#                        print(f"🛰️  {raw_hex} [Buffer/Search] ID:{msg_id}")
#                    else:
#                        # Show the Data
#                        print(f"{status_icon} {raw_hex} [{ts}] [{sensor_name}]")
                        
#                        if data_str:
#                            print(f"   └─ {data_str}")
                        
        except Exception as e:
            print(f"❌ CONNECTION ERROR: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
