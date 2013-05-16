#!/usr/bin/python

from __future__ import print_function

from dwarf import db

from dwarf.common import utils

IMAGES_INFO = ('created_at', 'id', 'is_public', 'links', 'name', 'size',
               'status', 'updated_at')


class Controller(object):

    def __init__(self):
        self.db = db.Controller()

    def list(self):
        """
        List all images
        """
        print('compute.images.list()')

        _images = self.db.images.list()
        return utils.sanitize(_images, IMAGES_INFO)

    def show(self, image_id):
        """
        Show image details
        """
        print('compute.images.show(image_id=%s)' % image_id)
        _image = self.db.images.show(id=image_id)
        return utils.sanitize(_image, IMAGES_INFO)
