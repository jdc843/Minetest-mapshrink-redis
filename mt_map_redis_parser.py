#!/usr/bin/env python

#Licence LGPL v2.1
#Created for version 25
#https://github.com/minetest/minetest/blob/944ffe9e532a3b2be686ef28c33313148760b1c9/doc/mapformat.txt

# Original Author: lag01 administrator of the JustTest MineTest server
# Edited by 843jdc


# PURPOSE:
# Parses a MineTest map of requested data called by another program.

# For some reason, I have to use "\xNUM", where NUM = a number, to be able to interpret
# what is read from a Redis database file.
# I don't know (yet!) what "\xNUM" is doing other than making this program work.
#
# int(binascii.hexlify(A), 16) -- Converts a single byte represented in '\x' notation
# into a proper integer that has a range of 0-255.
#
# When x is an integer, x == num is valid
# When x is a string, x == \xnum is valid
# Can use type(x) to show how x is stored: int or str
# This means that Redislite is reading int as strings!
# But it is also adding '\x' to the number string. Maybe. If so, why?
#
# To convert a byte read from Redis in \xnum format into a two character string, use:
# binascii.hexlify(string_byte_to_convert)
#
# To convert a byte read from Redis in \xnum format into an integer, use:
# int(binascii.hexlify(string_byte_to_convert), 16)

# NOTE: For all I know, I could have used the original struct.unpack commands
# But this method works! So I'm not testing that right now

#import struct
import zlib
import binascii

# It seems that this program doesn't inherit the Verbose variable from countowners.py
Verbose = 0

class MtRedisParser:
    'Allows to read data from a Minetest map block in a Redis database file'
    versionInt = 25
    flagsInt = None
    lightingInt = None
    content_widthInt = 2
    error = 0
    params_widthInt = 2
    length = None
    static_object_version = 0
    static_object_count = None
    objectsRead = ''
    timestamp = None
    name_id_mapping_version = 0
    num_name_id_mappings = None
    nameIdMappingsRead = ''
    nameIdMappings = None
    nodeDataRead = ''           # Uncompressed node data
    nodeMetadataRead = ''       # Uncompressed metadata for items in a mapblock.






    arrayParam0 = None          # Array of param0 values indexed by position
    arrayParam1 = None          # Array of param1 values
    arrayParam2 = None          # Array of param2 values


    metadata_version = 1        # Always 1.
    numNodesWMeta = 0           # Number of nodes within a mapblock that have metadata.
    arrayPosition = None        # Array: Position of each node with metadata.
    arrayNumVars = None         # Array: Number of how many Key|Value pairs each node has.
    arrayKeys = None            # Array: Key names for each nodes' variables. Example: owner
    arrayValues = None          # Array: Key values for each nodes' variables. Example: Admin
    inventoryBuf = None
    arraySI = None              # Array: Serialized Inventory for a node.
    arrayInventoryList = None   # Array: List of items in a nodes' inventory

    length_of_timer = 10
    num_of_timers = None
    timersRead = ''
    arrayTimerTimeout = None
    arrayTimerElapsed = None

# Not used because of my changes :
    arrayMetadataTypeId = None
    arrayMetadataRead = None




    def __init__(self, block):
        cursor = 0
        self.MappingID = {}
        self.nameIdMappings = {}




        self.arrayParam0 = {}
        self.arrayParam1 = {}
        self.arrayParam2 = {}
        self.numNodesWMeta = 0
        self.arrayPosition = {}
        self.arrayNumVars = {}
        self.arrayKeys = {}
        self.arrayValues = {}
        self.inventoryBuf = {}
        self.arraySI = {}
        self.arrayTimerTimeout = {}
        self.arrayTimerElapsed = {}
        self.length = len(block)
        self.MappingIDLen = {}
        self.MappingNames= {}
        self.nameIdMappingsRead = ""
# Not used because of my changes :
        self.arrayMetadataTypeId = {}
        self.arrayMetadataRead = {}
        self.arrayInventoryList = {}


# Map Format Version Number (unsigned char = 1 byte)
#       Ref serialization.h
        self.versionInt = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1


# Flags (unsigned char = 1 byte)
        self.flagsInt = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1


# Version 27 adds a u16 here for lighting. (unsigned short = 2 bytes)
        if self.versionInt >= 27:
            i = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
            cursor+= 1
            j = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
            cursor+= 1
            self.lightingInt = (i * 256) + j


# Content Width (unsigned char = 1 byte)
        self.content_widthInt = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        if self.versionInt <= 23 and self.content_widthInt != 1:
            print("Content width is wrong for this version!")
            self.error = 1
            return
        if self.versionInt >= 24 and self.content_widthInt != 2:
            print("Content width is wrong for this version!")
            self.error = 1
            return
        cursor+= 1


# Params Width (unsigned char = 1 byte)
        self.params_widthInt = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        if self.params_widthInt != 2:
            print("Params width not supported!")
            self.error = 1
            return
        cursor+= 1


# Node Data - compressed
        try:
            decompressor = zlib.decompressobj()
            self.nodeDataRead = decompressor.decompress( block[cursor:] )
            cursor = self.length - len(decompressor.unused_data)
        except:
            self.error = 1
            return


# Node Metadata - compressed
        try:
            decompressor = zlib.decompressobj()
            self.nodeMetadataRead = decompressor.decompress( block[cursor:] )
            cursor = self.length - len(decompressor.unused_data)
        except:
            self.error = 1
            return


# Node timers are here only if map version is less than 25
# If map version is 25 or greater, node timers are serialized later
        if self.versionInt <= 24:
            print("Node Timer parser for this map version is not written yet")
            self.error = 1
            return

# Static Objects
#       Read static object version (unsigned char = 1 byte)
        self.static_object_version = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        if self.static_object_version != 0:
            print("Static Object version not supported!")
            self.error = 1
            return
        cursor+=1

#       Read static objects. Store data in self.objectsRead. Do not parse it.
#       Read static object count (unsigned short = 2 bytes)
        i = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        j = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        self.static_object_count = (i * 256) + j
        for i in range(0, self.static_object_count):
#           Read each static objects's type (unsigned char = 1 byte)
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
#           Read each static objects's x,y,z position (signed int = 4 bytes)
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
#           Read each static object's y position (signed int = 4 bytes)
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
#           Read each static object's y position (signed int = 4 bytes)
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1

#           Read the data size (unsigned short = 2 bytes)
            j = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1
            k = binascii.hexlify(block[cursor:cursor + 1])
            self.objectsRead+= j
            cursor+= 1

#           Determine the size of the data to be read
            data_size = (int(j, 16) * 256) + int(k, 16)
            for l in range(0, data_size):
                j = binascii.hexlify(block[cursor:cursor + 1])
                self.objectsRead+= j
                cursor+= 1

# Timestamp Read unsigned int (4 bytes)
        i = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        j = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        k = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        l = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        self.timestamp = ( i * 16777216) + (j * 65536) + (k * 256) + l


# Name-id mappings.
# Check version
# Read each name-id mapping.
#
# Modifies:
# self.name_id_mapping_version  INT     Name ID Mapping Version Number
# self.num_name_id_mappings     INT     Number of different nodes in this map block
# self.MappingID[]              INT     Mapping ID Number of each different node
# self.MappingNames[]           STR     List of the names of the different nodes
# self.nameIdMappingsRead[]     STR     Concantenated list of the names of the different nodes

#       Check name-id-mapping version number (unsigned char = 1 byte)
        self.name_id_mapping_version = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        if self.name_id_mapping_version != 0:
            print("Name-ID mapping version not supported!")
#            self.error = 1
#            return

#       Read and store the number of name-id mappings (unsigned short = 2 bytes)
        i = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        j = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
        cursor+= 1
        self.num_name_id_mappings = (i * 256) + j

#       Loop through the number of name-id mappings
#       Store each ID number,  its name, add it to list
        for i in range(0, self.num_name_id_mappings):
            j = binascii.hexlify(block[cursor:cursor + 1])
            cursor+= 1
            k = binascii.hexlify(block[cursor:cursor + 1])
            cursor+= 1
            itemID = (int(j, 16) * 256) + int(k, 16)
            self.MappingID[i] = itemID

            j = binascii.hexlify(block[cursor:cursor + 1])
            cursor+= 1
            k = binascii.hexlify(block[cursor:cursor + 1])
            cursor+= 1
            leng = (int(j, 16) * 256) + int(k, 16)
            m = ""
            for l in range(0, leng):
                j = chr(int(binascii.hexlify(block[cursor:cursor + 1]), 16))
                m = m + j
                cursor+= 1
            self.nameIdMappingsRead = self.nameIdMappingsRead + m
            self.MappingNames[i] = m



# For map version 25 only:
# Timers - Read each timer blob. Do not parse them
# Store the data in timersRead to possibly be parsed later.
#       Read (unsigned char = 1 byte)
        if self.versionInt >= 25:
            self.length_of_timer = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
#           Read num_of_timers (unsigned short = 2 bytes)
            cursor+= 1
            i = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
            cursor+= 1
            j = int(binascii.hexlify(block[cursor:cursor + 1]), 16)
            cursor+= 1
            self.num_of_timers = (i * 256) + j
#          Read each node timer
            for i in range(0, self.num_of_timers):
                self.timersRead+= binascii.hexlify(block[cursor:cursor + 10])
                cursor+= 10
            if self.length != cursor:
                print("Parsed length is wrong!")

        if Verbose == 1:
            print("Block Version Number = " + str(self.versionInt))
            print("Timestamp: " + str(self.timestamp))
            print("Flags: " + str(self.flagsInt))
            if self.versionInt >= 27:
                print("Lighting")
            print("Num static objects: " + str(self.static_object_count))
            print("num_name_id_mappings = " + str(self.num_name_id_mappings))
            print("ID: " + str(itemID) + " Name: " + m)
            print("Concantenated Names: " + self.nameIdMappingsRead)
            print("Number of timers: " + str(self.num_of_timers))
