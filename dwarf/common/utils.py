#!/usr/bin/python

import hashlib
import os
import random
import signal
import socket
import subprocess

from dwarf import exception


def sanitize(obj, keys):

    def _sanitize(obj, keys):
        fields = {}
        for k in keys:
            if k in obj:
                fields[k] = obj[k]
            elif k == 'links':
                fields[k] = []
            elif k == 'properties':
                fields[k] = {}
            else:
                fields[k] = None
        return fields

    if isinstance(obj, dict):
        return _sanitize(obj, keys)

    objs = []
    for o in obj:
        objs.append(_sanitize(o, keys))
    return objs


def show_request(req):
    print("---- BEGIN REQUEST HEADERS -----")
    for key in req.headers.keys():
        print('%s = %s' % (key, req.headers[key]))
    print("---- END REQUEST HEADERS -----")

#    if req.body:
#        print("---- BEGIN REQUEST BODY -----")
#        print('%s' % req.body)
#        print("---- END REQUEST BODY -----")


def get_local_ip():
    """
    Get the IP of the local machine
    """
    addr = '127.0.0.1'
    try:
        csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        csock.connect(('8.8.8.8', 80))
        (addr, _port) = csock.getsockname()
        csock.close()
    except socket.error:
        pass

    return addr


def generate_mac():
    """
    Generate a random MAC address
    """
    mac = [0x52, 0x54, 0x00,
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff),
           random.randint(0x00, 0xff)]
    return ':'.join(['%02x' % x for x in mac])


def get_ip(mac):
    """
    Get the IP associated with the given MAC address
    """
    addr = None
    leases = '/var/lib/libvirt/dnsmasq/default.leases'
    with open(leases, 'r') as fh:
        for line in fh.readlines():
            col = line.split()
            if col[1] == mac:
                addr = col[2]
                break

    return addr


def create_base_images(target_dir, image_file, image_id):
    """
    Create the boot and ephemeral disk base images if they don't exist
    """
    print('utils.create_base_images(target_dir=%s, image_file=%s, '
          'image_id=%s)' % (target_dir, image_file, image_id))

    # Boot disk base image
    sha1sum = hashlib.sha1(image_id).hexdigest()
    boot_disk = '%s/%s' % (target_dir, sha1sum)
    if not os.path.exists(boot_disk):
        try:
            execute(['qemu-img', 'convert', '-O', 'raw', image_file,
                     boot_disk])
        except:
            if os.path.exists(boot_disk):
                os.remove(boot_disk)
            raise

    # Ephemeral disk base image
    ephemeral_disk = '%s/ephemeral_0_10_None' % target_dir
    if not os.path.exists(ephemeral_disk):
        try:
            execute(['qemu-img', 'create', '-f', 'raw', ephemeral_disk, '10G'])
            execute(['mkfs.ext3', '-F', '-L', 'ephemeral0', ephemeral_disk])
        except:
            if os.path.exists(ephemeral_disk):
                os.remove(ephemeral_disk)
            raise

    return {'boot-disk': boot_disk, 'ephemeral-disk': ephemeral_disk}


def create_local_images(target_dir, base_images):
    """
    Create the boot and ephemeral disk images
    """
    print('utils.create_local_images(target_dir=%s, base_images=%s)' %
          (target_dir, base_images))

    # Boot disk (disk)
    disk = '%s/disk' % target_dir
    execute(['qemu-img', 'create', '-f', 'qcow2', '-o',
             'cluster_size=2M,backing_file=%s' % base_images['boot-disk'],
             disk])

    # Ephemeral disk (disk.local)
    # TODO: variable size
    disk_local = '%s/disk.local' % target_dir
    execute(['qemu-img', 'create', '-f', 'qcow2', '-o',
             'cluster_size=2M,backing_file=%s' % base_images['ephemeral-disk'],
             disk_local])

    return {'disk': disk, 'disk.local': disk_local}


def execute(cmd, check_exit_code=None, shell=False, run_as_root=False):
    """
    Helper function to execute a command
    """
    print('utils.execute(cmd=%s, check_exit_code=%s, shell=%s, '
          'run_as_root=%s)' % (cmd, check_exit_code, shell, run_as_root))

    def preexec_fn():
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    if check_exit_code is None:
        check_exit_code = [0]

    ignore_exit_code = False
    if isinstance(check_exit_code, bool):
        ignore_exit_code = not check_exit_code
        check_exit_code = [0]
    elif isinstance(check_exit_code, int):
        check_exit_code = [check_exit_code]

    if run_as_root and os.geteuid() != 0:
        cmd = ['sudo'] + cmd

    cmd = [str(i) for i in cmd]

    if shell:
        cmd = ' '.join(cmd)

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, close_fds=True, shell=shell,
                         preexec_fn=preexec_fn)
    (stdout, stderr) = p.communicate()
    p.stdin.close()
    exit_code = p.returncode

    if not ignore_exit_code and exit_code not in check_exit_code:
        raise exception.CommandExecutionFailure(code=exit_code,
                                                reason='cmd: %s, stdout: %s, '
                                                'stderr: %s' % (cmd, stdout,
                                                                stderr))

    if stdout:
        print('utils.execute(stdout=%s)' % stdout)
    if stderr:
        print('utils.execute(stderr=%s)' % stderr)
    return (stdout, stderr)
