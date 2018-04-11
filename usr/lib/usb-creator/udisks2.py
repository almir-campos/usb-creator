#! /usr/bin/env python3

# Udisks2 API reference: https://udisks.freedesktop.org/docs/latest/

import gi
# Make sure the right UDisks version is loaded
gi.require_version('UDisks', '2.0')
from gi.repository import UDisks, GLib
from os.path import exists
import os
import time


# Subclass dict class to overwrite the __missing__() method
# to implement autovivificious dictionaries:
# https://en.wikipedia.org/wiki/Autovivification#Python
class Tree(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class Udisks2():
    def __init__(self):
        super(Udisks2, self).__init__()
        self.no_options = GLib.Variant('a{sv}', {})
        self.devices = Tree()

    # Create multi-dimensional dictionary with drive/device/deviceinfo
    def fill_devices(self, flash_only=True):

        self.devices.clear()

        client = UDisks.Client.new_sync(None)
        manager = client.get_object_manager()
        objects = manager.get_objects()

        for o in objects:
            block = None
            partition = None
            fs = None
            drive = None
            device_path = ''
            fs_type = ''
            drive_path = ''
            add_device = False
            removable = False
            connectionbus = ''
            mount_point = ''
            total_size = 0
            free_size = 0

            block = o.get_block()
            if block is None:
                continue

            device_path = block.get_cached_property('Device').get_bytestring().decode('utf-8')
            fs_type = block.get_cached_property('IdType').get_string()
            drive_path = self.get_drive_from_device_path(device_path)
            total_size = (block.get_cached_property('Size').get_uint64() / 1024)

            if not exists(drive_path) or total_size == 0:
                continue

            # Mount point
            fs = o.get_filesystem()
            if fs is not None:
                mount_points = fs.get_cached_property('MountPoints').get_bytestring_array()
                if mount_points:
                    mount_point = mount_points[0]
                    if exists(mount_point):
                        total_size, free_size, used_size = self.get_mount_size(mount_point)

            # There are no partitions: set free size to total size
            partition = o.get_partition()
            if partition is None:
                free_size = total_size

            drive_name = block.get_cached_property('Drive').get_string()
            drive_obj = manager.get_object(drive_name)
            if drive_obj is None:
                continue
            drive = drive_obj.get_drive()
            removable = drive.get_cached_property("Removable").get_boolean()
            connectionbus = drive.get_cached_property("ConnectionBus").get_string()

            if flash_only:
                # Check for usb mounted flash drives
                if connectionbus == 'usb' and removable:
                    add_device = True
            else:
                add_device = True

            if add_device:

                print(('========== Device Info of: %s ==========' % device_path))
                print(('Drive name: %s' % drive_name))
                print(('FS Type: %s' % fs_type))
                print(('Mount point: %s' % mount_point))
                print(('Total size: %s' % total_size))
                print(('Free size: %s' % free_size))
                print(('ConnectionBus: %s' % connectionbus))
                print(('Removable: %s' % str(removable)))
                print(('======================================='))

                if device_path == drive_path:
                    # Drive information
                    self.devices[drive_path]['drive_object'] = drive
                    self.devices[drive_path]['partition_object'] = partition
                    self.devices[drive_path]['connectionbus'] = connectionbus
                    self.devices[drive_path]['removable'] = removable
                    self.devices[drive_path]['total_size'] = total_size
                    self.devices[drive_path]['free_size'] = free_size
                else:
                    # Partition information
                    self.devices[drive_path][device_path]['fs_object'] = fs
                    self.devices[drive_path][device_path]['fs_type'] = fs_type
                    self.devices[drive_path][device_path]['mount_point'] = mount_point
                    self.devices[drive_path][device_path]['total_size'] = total_size
                    self.devices[drive_path][device_path]['free_size'] = free_size

    def get_drives(self):
        drives = []
        for d in self.devices:
            if exists(d) and d not in drives:
                drives.append(d)
        return drives

    def get_drive_device_paths(self, drive):
        devices = []
        for d in self.devices[drive]:
            if exists(d) and d not in devices:
                devices.append(d)
        return devices

    # returns total/free/used tuple (Kb)
    def get_mount_size(self, mount_point):
        try:
            st = os.statvfs(mount_point)
        except:
            return (0, 0, 0)
        total = (st.f_blocks * st.f_frsize) / 1024
        free = (st.f_bavail * st.f_frsize) / 1024
        #print((">> %s: f_bavail:%d * f_frsize:%d = free:%d (%d Kb)" % (mount_point, st.f_bavail, st.f_frsize, (st.f_bavail * st.f_frsize), free)))
        used = ((st.f_blocks - st.f_bfree) * st.f_frsize) / 1024
        return (total, free, used)

    def get_drive_from_device_path(self, device_path):
        return device_path.rstrip('0123456789')

    # Adapted from udisk's test harness.
    # This is why the entire backend needs to be its own thread.
    def _mount_filesystem(self, fs):
        mount_points = []
        if fs is not None:
            '''Try to mount until it does not fail with "Busy".'''
            timeout = 10
            while timeout >= 0:
                try:
                    return fs.call_mount_sync(self.no_options, None)
                except GLib.GError as e:
                    if 'UDisks2.Error.AlreadyMounted' in e.message or \
                        not 'UDisks2.Error.DeviceBusy' in e.message:
                        break
                    print('Busy.')
                    time.sleep(0.3)
                    timeout -= 1
            if timeout >= 0:
                mount_points = fs.get_cached_property('MountPoints').get_bytestring_array()
            else:
                raise
        if mount_points:
            return mount_points[0]
        else:
            return ''

    def mount_device(self, device_path):
        drive = self.get_drive_from_device_path(device_path)
        fs = self.devices[drive][device_path]['fs_object']
        mount = self._mount_filesystem(fs)
        if mount != '':
            # Set mount point and free space for this device
            total, free, used = self.get_mount_size(mount)
            self.devices[drive][device_path]['mount_point'] = mount
            self.devices[drive][device_path]['free_size'] = free
        return mount

    def _unmount_filesystem(self, fs):
        try:
            return fs.call_unmount_sync(self.no_options, None)
        except:
            raise

    def unmount_device(self, device_path):
        drive = self.get_drive_from_device_path(device_path)
        fs = self.devices[drive][device_path]['fs_object']
        return self._unmount_filesystem(fs)

    def unmount_drive(self, drive_path):
        for device_path in self.get_drive_device_paths(drive_path):
            fs = self.devices[drive_path][device_path]['fs_object']
            self._unmount_filesystem(fs)

    def poweroff_drive(self, drive_path):
        try:
            drive = self.devices[drive_path]['drive_object']
            return drive.call_power_off_sync(self.no_options, None)
        except:
            raise

    def set_filesystem_label(self, fs, label):
        try:
            return fs.set_label_sync(label, self.no_options, None)
        except:
            raise

    def set_filesystem_label_by_device(self, device_path, label):
        fs = self.devices[device_path]['fs_object']
        return self.set_filesystem_label(fs, label)

    def set_partition_bootable(self, partition):
        try:
            return partition.SetFlags(7, self.no_options)
        except:
            raise

    def set_partition_bootable_by_device_path(self, device_path):
        partition = self.devices[device_path]['partition_object']
        return self.set_partition_bootable(partition)

    def set_partition_label(self, partition, label):
        try:
            return partition.SetName(label, self.no_options)
        except:
            raise

    def set_partition_label_by_device_path(self, device_path, label):
        partition = self.devices[device_path]['partition_object']
        return self.set_partition_label(partition, label)
