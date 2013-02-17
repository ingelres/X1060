#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author: François Ingelrest

import eyeD3, os, shutil, sys, tempfile

DEST_DIR = '/media/WALKMAN/MUSIC'
TEMP_DIR = tempfile.mkdtemp()


def checkDir(path):
    """ Return True if the given path exists, is a directory, and can be read/written """
    return os.path.exists(path) and os.path.isdir(path) and os.access(path, os.R_OK | os.W_OK | os.X_OK)


def sanitize(string):
    """ Replace characters that can't be used as filename by a space """
    for char in ('"', '*', '/', ':', '<', '>', '?', '\\', '|'):
        string = string.replace(char, '')

    if len(string) > 32:
        string = string[:32]

    return string.strip()


def copycover(mp3s, cover = None):
    """ Create a copy of each mp3, insert the cover, and move it to DEST_DIR """

    print '  -- / --',
    sys.stdout.flush()

    for i, oldmp3 in enumerate(mp3s):

        # Show current progress
        print '\b\b\b\b\b\b\b\b%02u / %02u' % (i+1, len(mp3s)),
        sys.stdout.flush()

        # Get the tags we need
        input     = eyeD3.Mp3AudioFile(oldmp3)
        disc      = input.getTag().getDiscNum()[0]
        track     = input.getTag().getTrackNum()[0]
        title     = input.getTag().getTitle()
        album     = input.getTag().getAlbum()
        artist    = input.getTag().getArtist()
        performer = None

        # Is there a 'performer' tag (TPE2)?
        for frame in input.getTag().frames:
            if frame.header.id == 'TPE2':
                artist    = frame.text
                performer = artist
                break

        # Make sure it's not already there
        if disc is not None and disc != 0:
            album = album + ' [' + str(disc) + ']'

        destmp3 = os.path.join(DEST_DIR, sanitize(artist), sanitize(album), '%02u - %s.mp3' % (track, sanitize(title)))

        if os.path.exists(destmp3):
            print 'W "%s" already exists, SKIPPING' % destmp3
            continue

        # Create a working copy of the file
        newmp3 = os.path.join(TEMP_DIR, os.path.basename(oldmp3))
        shutil.copy(oldmp3, newmp3)

        # Incorporate the Disc number into the title if needed
        # Also replace the artist by the performer if any
        if (disc is not None and disc != 0) or performer is not None:
            input = eyeD3.Mp3AudioFile(newmp3)

            if performer is not None:
                input.getTag().setArtist(performer)

            if disc is not None and disc != 0:
                input.getTag().setAlbum(album)

            input.getTag().update()

        # Convert tags to the correct version, and remove existing images (the walkman doesn't like to find many images)
        os.system('eyeD3 --to-v2.3 --remove-comments --remove-images "%s" > /dev/null 2>&1' % (newmp3))

        # Insert the cover
        if cover is not None:
            os.system('eyeD3 --add-image="%s":FRONT_COVER "%s" > /dev/null 2>&1' % (cover, newmp3))

        # Create the hierarchy of directories if needed
        if not os.path.exists(os.path.split(destmp3)[0]):
            os.makedirs(os.path.split(destmp3)[0])

        # We're done, we can finally move the file
        shutil.move(newmp3, destmp3)

    print '\b\b\b\b\b\b\b\b\b\b',
    sys.stdout.flush()


def mp3walk(directory):
    """
        Recursively go through the given directory and find MP3 files
        When some are found:
            * The cover is inserted (if one found) in a copy of the file,
            * Which is then copied to DEST_DIR
    """
    print
    print '  Processing "%s"' % directory

    # Split the contents of directory
    mp3s, pics, dirs = [], [], []

    for child in [os.path.join(directory, child) for child in os.listdir(directory)]:
        if os.path.isdir(child):
            dirs.append(child)
        elif os.path.isfile(child):
            ext = os.path.splitext(child.lower())[1]

            if ext == '.mp3':              mp3s.append(child)
            elif ext in ('.jpg', '.jpeg'): pics.append(child)

    # Process the mp3s we have found
    if len(mp3s) == 0:
        print 'W No MP3 files found in "%s"' % directory
    else:
        if len(pics) == 0:
            print 'W No cover found in "%s", looking in the parent directory...' % directory

            parent = os.path.join(directory, '..')

            for child in [os.path.join(parent, child) for child in os.listdir(parent)]:
                if os.path.isfile(child) and os.path.splitext(child.lower())[1] in ('.jpg', '.jpeg'):
                    pics.append(child)
                    break

            if len(pics) == 0:
                print 'W No cover found...'
                copycover(mp3s)
            else:
                print '  Using image "%s"' % os.path.basename(pics[0])
                copycover(mp3s, pics[0])

        else:
            print '  Using image "%s"' % os.path.basename(pics[0])
            copycover(mp3s, pics[0])

        print ' Processed %u MP3 files' % len(mp3s)

    # Process all subdirectories
    for subdirectory in dirs:
        mp3walk(subdirectory)


# ----==== ENTRY POINT ====----


# Check command line
if len(sys.argv) < 2:
    print 'USAGE: %s directory [directory2 ...]' % os.path.basename(sys.argv[0])
    sys.exit(1)

# Make sure we can copy the mp3s to the destination
if not checkDir(DEST_DIR):
    print 'Destination "%s" is not a directory, or cannot be accessed' % DEST_DIR
    sys.exit(2)

# Process each given directory
for directory in sys.argv[1:]:

    if not checkDir(directory):
        print 'Source "%s" is not a directory, or cannot be accessed: SKIPPING' % directory
        continue

    mp3walk(directory)

# Remove the temp directory before leaving
shutil.rmtree(TEMP_DIR)
