#!/usr/bin/env python


from os import urandom
from os.path import exists, isdir
from optparse import OptionParser
from random import seed, randrange
from PIL import Image


def load_img(img_path):
  if not exists(img_path) or isdir(img_path):
    raise ValueError('Invalid image path.')

  img = Image.open(img_path)
  #if img.mode != 'RGB':
  #  raise NotImplementedError('Non-RBG images are not yet supported.')

  return img


def encode(img_path, msg):
  img, msg_len = load_img(img_path), len(msg)
  enc, w, h = img.copy(), *img.size
  seen_pixels = [(0, 0), (0, 1)]

  #big ol' message eh?
  if msg_len > w*h:
    raise OverflowError('Message too long to encode.')

  #encode msg len into r at pixel (0, 0)
  rgba = [*img.getpixel((0, 0))]
  rgba[0] = msg_len
  enc.putpixel((0, 0), tuple(rgba))

  #encode cryptographically secure random 3 byte seed into rgb at pixel (0, 1)
  #NOTE: 255 * 255 * 255 = 16,581,375
  s = urandom(3)
  seed(s)
  rgba = [*img.getpixel((0, 1))]
  rgba[0:3] = s[0:3]
  enc.putpixel((0, 1), tuple(rgba))

  #encode msg into r at seeded random pixel
  for i in range(msg_len):
    cur_xy = (randrange(w), randrange(h))
    while cur_xy in seen_pixels:
      cur_xy = (randrange(w), randrange(h))

    seen_pixels.append(cur_xy)

    rgba = [*img.getpixel(cur_xy)]
    rgba[0] = ord(msg[i]) 
    enc.putpixel(cur_xy, tuple(rgba))

  enc.save(f'enc_{img_path}')


def decode(img_path):
  img = load_img(img_path)
  w, h = img.size
  seen_pixels = [(0, 0), (0, 1)]
  msg_len = [*img.getpixel((0, 0))][0]
  rgba = [*img.getpixel((0, 1))]
  s = rgba[0].to_bytes(1, 'big') + rgba[1].to_bytes(1, 'big') + rgba[2].to_bytes(1, 'big')
  seed(s)

  out = ''
  for _ in range(msg_len):
    cur_xy = (randrange(w), randrange(h))
    while cur_xy in seen_pixels:
      cur_xy = (randrange(w), randrange(h))

    seen_pixels.append(cur_xy)
    out += chr([*img.getpixel(cur_xy)][0])

  return out


if __name__ == '__main__':
  usage = 'usage: %prog [options] <message>'
  parser = OptionParser(usage)
  parser.add_option('-d', '--decode', action='store_true', dest='decode', default=False, help='decode text from an image')
  parser.add_option('-e', '--encode', action='store_true', dest='encode', default=False, help='encode text into an image')
  parser.add_option('-f', '--file', action='store', metavar='FILE', help='the path to the image')
  opts, args = parser.parse_args()

  if opts.encode and opts.decode:
    raise parser.error('Options -e and -d are mutually exclusive.')

  if not opts.file:
    raise parser.error('Option -f is required.')
  
  if opts.encode:
    if len(args) < 1:
      raise parser.error('Missing <message> argument.')

    encode(opts.file, ' '.join(args))
  elif opts.decode:
    print(decode(opts.file))

