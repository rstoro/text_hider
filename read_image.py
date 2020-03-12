#!/usr/bin/env python


class Image(object):
  def __init__(self, image_name):
    self._chunks = []
    self._image_name = image_name

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

      while True:
        #current chunk
        length = f.read(4)
        type_or_name = f.read(4)
        data = f.read(int.from_bytes(length, 'big'))
        crc_checksum = f.read(4)

        #store chunk
        self._chunks.append(length + type_or_name + data + crc_checksum)

        readable_type_or_name = type_or_name.decode('UTF-8')
        #critical chunks - NOTE: we do not really care about ancillary chunks
        if readable_type_or_name == 'IHDR':
          self.width = int.from_bytes(data[0:4], 'big')
          self.height = int.from_bytes(data[4:8], 'big')
          self._bit_depth = data[8]   #bit depth determines channel used
          self._color_type = data[9]
          self._is_alpha = bool((self._color_type & 0b00000100) >> 2)

          color_type = data[9]
          compression_method = data[10]
          filter_method = data[11]
          interlace_method = data[12]
        elif readable_type_or_name == 'IDAT':
          data_ref = [self._chunks[-1]]
        elif readable_type_or_name == 'IEND':
          break 

    def save(self):
      #write out bs to file
      with open('test_' + self._image_name, 'x') as f:
        for chunk in self._chunks:
          f.write(chunk)


if __name__ == '__main__':
  #TESTING
  image_files = ['base_img.png', 'Station300_TransparentBackground_dark.png']
  for image_file in image_files:
    img = Image(image_file)


