from aseprite import AsepriteFile
import numpy as np
import binascii
import struct
import zlib
import copy as cp

np.set_printoptions(edgeitems=3,infstr='inf',
                    linewidth=75, nanstr='nan', precision=8,
                    suppress=False, threshold=1000, formatter=None)

def aseprite_to_numpy(file_path):
    # Read file using py_aseprite
    with open(file_path, "rb") as f:
        a = f.read()
        parsed_file = AsepriteFile(a)
        frames = parsed_file.frames
        header = parsed_file.header

    #Check sice of color values
    if header.color_depth == 8:
        color_size = 2
    elif header.color_depth == 16:
        color_size = 4
    else:
        raise ValueError("Unknown color depth: {}".format(header.color_depth))

    #Check if there are used multiple layers
    if frames[0].num_chunks == 4:
        layers = False
    elif frames[0].num_chunks == 6:
        layers = True
    else:
        raise ValueError("Unkonwn number of chunks in first frame: {}".format(frames[0].num_chunks))
    
    width, height = header.width, header.height
    animation = []
    for i, frame in enumerate(frames):
        for chunk in frame.chunks:
            # Only insterested in the chunks containing the data
            if chunk.chunk_type == 0x2005:
                # Make sure to use the right layer index dependent on wether multiple layers are used or not
                if (layers and chunk.layer_index == 1) or (not layers and chunk.layer_index == 0):
                    chunk_width, chunk_height = int(chunk.data["width"]), int(chunk.data["height"])
                    frame = np.zeros((width, height), dtype="uint8")
                    data = binascii.hexlify(chunk.data["data"])
                    cnt_x = chunk.x_pos
                    cnt_y = chunk.y_pos
                    for i in range(chunk_width * chunk_height):
                        #Wors way ever to convert from byres to int...
                        val = data[i*color_size:i*color_size+color_size]
                        val = val[0:2]
                        val_str = "{}".format(val)[1:]
                        val_int = int(val, 16)
                        #If grayscale are used, flip the scale
                        if color_size == 4:
                            val_int = 255 - val_int
                        frame[cnt_x, cnt_y] = val_int
                        cnt_x += 1
                        if cnt_x == chunk_width + chunk.x_pos:
                            cnt_x  = chunk.x_pos
                            cnt_y += 1
                    animation.append(frame)
    return animation

def numpy_to_fetch(animation, outfile="out", scale_from=1, scale_to=1):
    num_frames = len(animation)
    num_x, num_y = animation[0].shape
    pwm_frames = []
    with open("{}.bin".format(outfile), "wb") as fp:
        for i in range(num_frames):
            frame = cp.deepcopy(animation[i])
            frame = frame.transpose()
            frame = np.flip(frame, 0)
            binary_factors = 2**np.linspace(0,num_y, num_y+1)[0:-1]
    
            binary_frame_matrix = (frame > 0)
            binary_frame_array = np.sum(binary_frame_matrix * binary_factors.reshape(-1,1), 0)
            binary_frame_array_uint32 = np.uint32(binary_frame_array.astype(int))
    
            frame[frame == 0] = 20
            pwm_frame_uint8 = np.uint8(frame) * scale_to / scale_from
            
            fp.write(bytes(binary_frame_array_uint32))
            pwm_frames.append(pwm_frame_uint8)
    
        for pwm_frame in pwm_frames:
            fp.write(bytes(pwm_frame))

    with open("{}.txt".format(outfile), "w") as fp:
        fp.write("{},{},{},0,0,1,0,-1,0,-1,0".format(num_x, num_y, num_frames))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("No file path given...")
    else:
        animation_np = aseprite_to_numpy(sys.argv[1])
        numpy_to_fetch(animation_np)