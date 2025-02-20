import struct

test_str = "Hello, World!"
p = struct.pack("I", len(test_str))
print(p)
up = struct.unpack("I", p)
print(up[0])