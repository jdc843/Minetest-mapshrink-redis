#!/usr/bin/env python

"""
    PURPOSE:
        Stand-alone Redis-based mapshrink for MineTest.

    Licence:
        LGPL v2.1

    Authors/Credits:
        Orignal Author : Lag <need his git repo name>
        Maikerumine?
        Heavily modified by 843jdc

    Some of the Python Modules Required:
        binascii
        redislite:
            Get the module from: https://github.com/yahoo/redislite
            Read the docs at: http://redislite.readthedocs.io/en/latest/
            Uses an existing runing Redis server
            or creates one itself using a specified database file
"""

import sys #to get parameters
import operator
import sqlite3
import redislite
import re
from time import ctime
from copy import copy

import mt_map_redis_parser

sourceHash = "IGNORED"
destinationHash = "IGNORED"

worldDir = r'/path/to/Minetest/Map'
sourceName = worldDir + '/cashs-world.rdb'
destinationName = worldDir + '/cashs-world-new.rdb'
errorFileName = worldDir + r'/errors.txt'

searchMode = "Mapshrink"
radius = 7
verbose = 1


#use compiled regular expression to filter blocks by block content. it is faster that checking "in array".
quickCombinedSearch = re.compile('(custom|default):chest_locked|(custom|protector):protect2|(custom|protector):protect|custom:protected_chest|protector:chest')
#quickCombinedSearch = re.compile('(custom|default):stone_with_gold')
#quickCombinedSearch = re.compile('protector:chest')
item = {}
item[1] = "custom:chest_locked"
item[2] = "default:chest_locked"
item[3] = "custom:protect2"
item[4] = "protector:protect2"
item[5] = "custom:protect"
item[6] = "protector:protect"
item[7] = "custom:protected_chest"
item[8] = "protector:chest"
numItems = 8

# Change this timeout value if you have a really large map file.
class Conn(redislite.StrictRedis):
    start_timeout = 180

print("Mapshrink Start Time: " + ctime())

# Convert an X, Y, Z tuple into an integer
def getXYZAsInteger(p):
    """Takes a xyz tuple and returns an int
    p[0] = X
    p[1] = Y / 4096 map blocks
    p[2] = Z / 4096 map blocks
    """
    return int64(p[2]*16777216 + p[1]*4096 + p[0])

def int64(u):
    while u >= 2**63:
        u -= 2**64
    while u <= -2**63:
        u += 2**64
    return u

# Convert an integer into a X, Y, Z tuple
def getIntegerAsXYZ(i):
    """Takes an int and returns a xyz tuple
    [0] = X
    [1] = Y
    [2] = Z
    """
    x = unsignedToSigned(i % 4096, 2048)
    i = int((i - x) / 4096)
    y = unsignedToSigned(i % 4096, 2048)
    i = int((i - y) / 4096)
    z = unsignedToSigned(i % 4096, 2048)
    return x,y,z

def unsignedToSigned(i, max_positive):
    if i < max_positive:
        return i
    else:
        return i - 2*max_positive


def redisMapshrink():
    print("Determining how many map blocks this database has ... "),
    keys = sourceConn.hkeys(sourceHash)
    numberOfMapblocks = sourceConn.hlen(sourceHash)

#   Just in case:
    if numberOfMapblocks != len(keys):
        print("ERROR: The number of map blocks does not equal the number of keys!")
        return

#   Is it even possible for a database file to have no records? Just in case:
    if numberOfMapblocks == 0:
        print("Map has no mapblocks!")
        sourceConn.shutdown()
        quit()
    print("numberOfMapblocks: " + str(numberOfMapblocks))

#   Find map blocks that contain search items. Save their key to the array saveThese1. Save count to save1Count
    print("Pass #1: Search for map blocks that contain the desired items")
    saveThese1 = []
    save1Count = 0
    for n in range(0, numberOfMapblocks):
        # Convert keys from a list of text strings representing integers to a list of integers
        keys[n] = int(keys[n])
        block = sourceConn.hget(sourceHash, keys[n])
        if block != None or block != '':
            BlockData = mt_map_redis_parser.MtRedisParser(block)
            if BlockData.error != 0:
                print("***************Error while reading map block # " + str(keys[n]))
                with open(errorFileName, "a") as text_file:
                    text_file.write("Error while reading map block # " + str(keys[n]))
                text_file.closed
                continue
            if quickCombinedSearch.search(BlockData.nameIdMappingsRead) != None:
                saveThese1.append(keys[n])
                save1Count+= 1
    print("Number of map blocks searched: " + str(numberOfMapblocks))
    print("Number of map blocks that contain search items: " + str(save1Count))
    print("Location of search items: " + str(saveThese1[save1Count-1]) + "  " + str(getIntegerAsXYZ(saveThese1[save1Count-1])))

    if save1Count == 0:
        print("No map blocks contain any of the search items!")
        return

# Get each map block number that is being saved in the first pass. Add to them in all directions.
# Map boundary check. Then save the result to saveThese2
    print("Pass #2: Collect map blocks in radius")
    save2Count = (radius * 2 + 1) * (radius * 2 + 1) * (radius * 2 + 1)
    saveThese2 = [[0 for x in range(save2Count)] for y in range(save1Count)]
    outOfBounds = 0
    print("Mapshrink save radius: " + str(radius))
    for n in range(0, save1Count):
        s = list(getIntegerAsXYZ(saveThese1[n]))
        q = copy(s)
        save2Count = 0
        print("Checking item #: " + str(n + 1) + "   of " + str(save1Count) + "\x0D"),
        for x in range(-radius, radius + 1):
            for y in range(-radius, radius + 1):
                for z in range(-radius, radius + 1):
#                   Boundary checks
                    q[0] = s[0] + x
                    if q[0] > 2047:
                        q[0] = 2047
                        outOfBounds+= 1
                        continue
                    if q[0] < -2048:
                        q[0] = -2048
                        outOfBounds+= 1
                        continue
                    q[1] = s[1] + y
                    if q[1] > 2047:
                        q[1] = 2047
                        outOfBounds+= 1
                        continue
                    if q[1] < -2048:
                        q[1] = -2048
                        outOfBounds+= 1
                        continue
                    q[2] = s[2] + z
                    if q[2] > 2047:
                        q[2] = 2047
                        outOfBounds+= 1
                        continue
                    if q[2] < -2048:
                        q[2] = -2048
                        outOfBounds+= 1
                        continue
                    r = getXYZAsInteger(q)
                    saveThese2[n][save2Count] = r
                    save2Count+= 1

# Map block numbers in saveThese2 may not actually exist in the database file

    print("Starting a Redis server to save the selected map blocks to")
    class Conn(redislite.StrictRedis):
        start_timeout = 180
    destinationConn = Conn(destinationName)
    print("Redis server started")
    for n in range(0, save1Count):
        print("Saving item block #: " + str(n) + "   of " + str(save1Count))
        # Number of map blocks that surround each n. radius 1 = 27, radius 2 = 125
        for p in range(0,save2Count):
            # Get the map block data from the source
            if sourceConn.hexists(sourceHash, saveThese2[n][p]) == 1:
                mapBlockData = sourceConn.hget(sourceHash, saveThese2[n][p])
                # Put the map block data into the destination
                destinationConn.hset(destinationHash, saveThese2[n][p], mapBlockData)
    # Insure that the key never expires
    destinationConn.persist(destinationHash)
    print("\x0A" + "Save complete."),
    saved = destinationConn.hlen(destinationHash)
    print(" " + str(saved) + " Map blocks saved to new database")
    print("Shutting down destination server")
    destinationConn.shutdown()



print("Starting a Redis server")
sourceConn = Conn(sourceName)
print("Redis server started")
redisMapshrink()
print("Stopping Redis server")
sourceConn.shutdown()
print("Redis server stopped")

print("Search Stop Time: " + ctime() + "\x0A")
