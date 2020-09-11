#!/usr/bin/env python3

import click 
import socket
import struct
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)

TFTP_OP = {
        'rrq': 1,
        'wrq': 2,
        'data': 3,
        'ack': 4,
        'error': 5
    }

def fetch(server, filename):
    request = bytes()
    # pack byte for read opcode 1
    opcode = struct.pack('!H', 1)
    request += opcode

    filename = bytes(filename.encode('utf-8'))
    request += filename

    # 1 byte 0
    request += struct.pack('!B', 0)

    # append the mode of transfer
    mode = bytes('octet'.encode('utf-8'))
    request += mode
    # append the last byte
    request += struct.pack('!B', 0)

    # print(f"Request {request}")
    sock.sendto(request, (server, 69))




def ack(server=None, blk_num=None):
    ack = struct.pack('!H', TFTP_OP['ack'])
    ack += blk_num
    # print('ack:', ack)
    sock.sendto(ack, server)
    # print('number bytes:', sent)



def data_response(file, server, data, blk_num):
    """Response to data
    Args:
        file: the file to write to
        server: the server to respond to
        data: server responsed bytes
        blk_num: the previous block number
    Return:
        True if all 512 bytes are used -> continue
        False packet data less than 512 -> terminate(acked already)
    """
    # check duplicate
    [this_blk] = struct.unpack('!H', data[2:4])
    # update blk and write only if not duplicate
    if this_blk != blk_num:
        # write data to file
        file.write(data[4:])
    # print('data length: ', len(data[4:]))
    # ack the block number
    ack(server, data[2:4])
    return (len(data[4:]) <= 511, this_blk)

def error_response(data):
    """Response to error
    Args:
        data: the server returned data with error message
    """
    [error_code] = struct.unpack('!H', data[2:4])
    error_msg = data[4:].decode("utf-8")
    # print error code and massage
    print('Error Code {}: {}'.format(error_code, error_msg))
    sys.exit(error_code)

@click.command()
@click.argument('tftp_server')
@click.argument('filename')
def main(tftp_server, filename):
    """Fetch a file called filename from a TFTP server running on tftp_server.
    Returns 0 on success; otherwise, the return code will be the error code
    from the server.
    
    TFTP_SERVER The address of TFTP server.

    FILENAME The file to fetch.
    """
    # print('start')
    try:
        # bind local server
        # if local:
            # sock.bind((tftp_server, 2020))
        # else:
        #     sock.connect((tftp_server, 2020))
        fetch(tftp_server, filename)
        file = open(filename, "wb")
        byte_re = 0
        blk_num = 0
        data = None
        server = None

        while True:
            try:
                # Wait for the data from the server
                data, server = sock.recvfrom(600)
            except socket.timeout:
                if sock.gettimeout() > 10 or blk_num == 0:
                    print('Timeout communicating with {}'.format(tftp_server))
                    sys.exit(1)
                if blk_num > 0:
                    # packet may lost on timeout -> resend previous ACK
                    ack(server, data[2:4])
                    sock.settimeout((sock.gettimeout())*2)
                    

            # print('data:', data[0:4])
            # print('server:', server)
            # get opcode in int
            [opcode] = struct.unpack('!H', data[:2])
            if opcode == TFTP_OP['data']:
                byte_re += len(data[4:])
                end, blk_num = data_response(file, server, data, blk_num)
                if end:
                    # Received byte summary
                    print('Received {} bytes'.format(byte_re))
                    sock.close()
                    file.close()
                    break
            elif opcode == TFTP_OP['error']:
                error_response(data)
            else:
                sock.close()
                file.close()
                break
    except socket.timeout:
        print('Timeout communicating with {}'.format(tftp_server))
        sys.exit(1)


if __name__ == '__main__':
    main()
