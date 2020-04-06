#!/usr/bin/env python


class Crc32(object):
  def __init__(self):
    self._crc_table = [0] * 256
    for i in range(256):
      crc = i
      for j in range(8):
        if crc & 1:
          crc = ((crc >> 1) & 0x7FFFFFFF) ^ 0xEDB88320 #crc32 polynomial
        else:
          crc = ((crc >> 1) & 0x7FFFFFFF)
      self._crc_table[i] = crc


  def get(self, bs):
    value = 0xFFFFFFFF
    for i in range(len(bs)):
      value = self._crc_table[(bs[i] ^ value) & 0xff] ^ ((value >> 8) & 0xFFFFFF)

    return value ^ 0xFFFFFFFF


  def combine(self, crc1, crc2, len2):
    if len2 <= 0:
      return crc1

    odd = [0xEDB88320] + [1 << i for i in range(31)]
    even = [0] * 32

    def matrix_mult(matrix, vector):
      number_sum = 0
      matrix_i = 0
      while vector != 0:
        if vector & 1:
          number_sum ^= matrix[matrix_i]
        vector = vector >> 1 & 0x7FFFFFFF
        matrix_i += 1
      return number_sum

    even[:] = [matrix_mult(odd, odd[n]) for n in range(0, 32)]
    odd[:] = [matrix_mult(even, even[n]) for n in range(0, 32)]
    while len2 != 0:
      even[:] = [matrix_mult(odd, odd[n]) for n in range(0, 32)]

      if len2 & 1:
        crc1 = matrix_mult(even, crc1)
      len2 = len2 >> 1

      if len2 == 0:
        break
      odd[:] = [matrix_mult(even, even[n]) for n in range(0, 32)]

      if len2 & 1:
        crc1 = matrix_mult(odd, crc1)
      len2 = len2 >>  1

    crc1 ^= crc2
    return crc1


class Image(object):
  #NOTE: All integers larger than one byte are stored in network byte order!!!
  def __init__(self, image_name):
    self._chunks = []
    self._image_name = image_name
    self._crc = Crc32()

    with open(self._image_name, 'rb') as f:
      #file header
      most_significant_bit = f.read(1)
      image_type = f.read(3)
      carriage_return = f.read(1)
      line_feed_one = f.read(1)
      ctrl_or_carrot_z = f.read(1)
      line_feed_two = f.read(1)

      #check to see if it is a png
      if not (most_significant_bit.hex() == '89' and image_type.hex() == '504e47' \
          and carriage_return.hex() == '0d' and line_feed_one.hex() == '0a' \
          and ctrl_or_carrot_z.hex() == '1a' and line_feed_two.hex() == '0a'):
        raise ValueError('Image provided is not a PNG.')

      #add file header to chunks
      self._chunks.append(most_significant_bit + image_type + carriage_return + line_feed_one + ctrl_or_carrot_z + line_feed_two)

      #get chunks
      while True:
        #current chunk
        length = f.read(4)
        type_or_name = f.read(4)
        data = f.read(int.from_bytes(length, 'big'))
        crc_checksum = f.read(4)

        #verify checksum
        assert(self._crc.combine(self._crc.get(type_or_name), self._crc.get(data), len(data)).to_bytes(4, 'big') == crc_checksum)
        #TODO: if this check fails, fix data

        #store chunk in memory
        self._chunks.append((length, type_or_name, data, crc_checksum))

        #critical chunks - NOTE: we do not really care about ancillary chunks
        readable_type_or_name = type_or_name.decode('UTF-8')

        #DEBUG
        print(readable_type_or_name)

        if readable_type_or_name == 'IHDR':   #header
          self.width = int.from_bytes(data[0:4], 'big')
          self.height = int.from_bytes(data[4:8], 'big')
          self._bit_depth = data[8]   #bit depth determines channel used
          self._color_type = data[9]
          self._compression_method = data[10]
          self._filter_method = data[11]
          self._interlace_method = data[12]
          self._is_alpha = bool((self._color_type & 0b00000100) >> 2)

          #DEBUG
          print('\twidth, height:',self.width, self.height)
          print('\tbit_depth:', self._bit_depth)
          print('\tcolor_type:', self._color_type)
          print('\tcompression_method:', self._compression_method)
          print('\tfilter_method:', self._filter_method)
          print('\tinterlace_method:', self._interlace_method)
          print('\tis_alpha:', self._is_alpha)
        elif readable_type_or_name == 'PLTE':   #palette being used
          #NOTE: cannot have palette with alpha stored without some hacks https://www.maptiler.com/news/2008/11/png-palette-with-variable-alpha-small/
          #broken into 3 byte chunks of hex color map
          self._palette = [(data[i], data[i+1], data[i+2]) for i in range(0, len(data), 3)]

          #DEBUG
          print('\t', self._palette)
        elif readable_type_or_name == 'IDAT':   #image pixels
          '''
             _____________________________________________
            |       |           |     binary    |         |
            | color |   name    |---------------|  mask   |
            | type  |           |   | A | C | P |         |
            |_______|___________|___|___|___|___|_________|
            |       |           |   |   |   |   |         |
            |   0   | grayscale | 0 | 0 | 0 | 0 |         |
            |_______|___________|___|___|___|___|_________|
            |       |           |   |   |   |   |         |
            |   2   | truecolor | 0 | 0 | 1 | 0 |  color  |
            |_______|___________|___|___|___|___|_________|
            |       |           |   |   |   |   |  color  |
            |   3   |  indexed  | 0 | 0 | 1 | 1 | palette |
            |_______|___________|___|___|___|___|_________|
            |       | grayscale |   |   |   |   |         |
            |   4   | and alpha | 0 | 1 | 0 | 0 |  alpha  |
            |_______|___________|___|___|___|___|_________|
            |       | truecolor |   |   |   |   |  alpha  |
            |   6   | and alpha | 0 | 1 | 1 | 0 |  color  |
            |_______|___________|___|___|___|___|_________|
          '''
          #TODO: deinterlace
          #layout and total sized determined by IHDR chunk
          #compression method #filter method #interlace method
          #for scanline in len(0, data, self._bit_depth)
          
          #palette is a map of reused color values
          for bits in range(0, len(data), self._bit_depth):
            if self._palette:
              print(data[::-1][bits], end='|' if bits+self._bit_depth != len(data) else '\n')
              pass
            elif self._is_alpha:
              pass
            else:
              pass
        elif readable_type_or_name == 'IEND':   #end
          break 


  def save(self):
    #write out bs to file
    with open('test_' + self._image_name, 'x') as f:
      for chunk in self._chunks:
        length, type_or_name, data, old_crc_checksum = chunk
        #TODO: remake checksums (crc32) for each chunk
        f.write(length + type_or_name + data + old_crc_checksum)


  def get_filter_from_type(self, filter_type):
    def _none(scanline):
      return scanline

    def _sub(scanline):
      return scanline

    def _up(scanline):
      return scanline

    def _average(scanline):
      return scanline

    def _paeth(scanline):
      return scanline

    return [_none, _sub, _up, _average, _paeth][filter_type]


if __name__ == '__main__':
  #TESTING
  image_files = ['palette_image.png','base_img.png', 'Station300_TransparentBackground_dark.png']
  img = Image(image_files[0])
  #for image_file in image_files:
  #  img = Image(image_file)


