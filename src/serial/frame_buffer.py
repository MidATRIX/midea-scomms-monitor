class FrameBuffer:
    def __init__(self):
        self.buffer = bytearray()
        
        # Valid Signatures Map: (Byte 0, Byte 3)
        self.VALID_COMMANDS = {
            (0xA0, 0x20),
            (0xA0, 0x21),
            (0xA0, 0x25),
            (0xA0, 0x50),
            (0xA0, 0x51),
            (0xA0, 0x52),
            (0xA0, 0x53),
            (0xA0, 0x91),
            (0xAA, 0xD4), 
            (0xAA, 0x00), 
            (0xA6, 0x64), 
            (0xA6, 0x25), 
        }

    def feed(self, data: bytes):
        self.buffer.extend(data)

    def _get_length(self) -> int:
        b0 = self.buffer[0]
        b1 = self.buffer[1]
        
        if b0 == 0xA0:
            return self.buffer[4] + (9 if b1 == 0x01 else 8)
            
        if b0 in (0xAA, 0xA6):
            return 11 if b1 == 0x01 else 10
            
        return -1

    def get_frame(self):
        noise = bytearray()
        
        while len(self.buffer) > 0:
            if len(self.buffer) < 5:
                return None, bytes(noise)
            
            b0 = self.buffer[0]
            b3 = self.buffer[3]
            signature = (b0, b3)
            
            if signature in self.VALID_COMMANDS:
                expected_len = self._get_length()
                
                if len(self.buffer) >= expected_len:
                    frame = bytes(self.buffer[:expected_len])
                    del self.buffer[:expected_len]
                    return frame, bytes(noise)
                else:
                    return None, bytes(noise)
            else:
                noise.append(self.buffer.pop(0))
        
        return None, bytes(noise)
