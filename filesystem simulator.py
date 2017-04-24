# this program simulates a small file system on linux by creating lots of files as blocks on real disks
# superBlock = {'creationTime':1376483073
#		'mounted':50,
#		'devId':20,
#		'freeStart':1,
#		'freeEnd':25,
#		'root':26,
#		'maxBlocks':10000
#		}
# dirInfo =    {'size':1033,
#		'uid':1000,
#		'gid':1000,
#		'mode':16877,
#		'atime':1323630836,
#		'ctime':1323630836,
#		'mtime':1323630836,
#		'linkcount':4,
#		'filename_to_inode_dict':      {'ffoo':1234,
#						'd.':102,
#						'd..':10,
#						'fbar':2245
#					        }
#		}
# rootdirInfo ={'size':0,
#		'uid':DEFAULT_UID,
#		'gid':DEFAULT_GID,
#		'mode':S_IFDIR | S_IRWXA,
#		'atime':1323630836,
#		'ctime':1323630836,
#		'mtime':1323630836,
#		'linkcount':2,
#		'filename_to_inode_dict':	{'d.':ROOTDIRECTORYINODE,
#						'd..':ROOTDIRECTORYINODE
#						}
#		}
# inodeInfo = {	'size':1033,
#		'uid':1000,
#		'gid':1000,
#		'mode':33261,
#		'linkcount':2,
#		'atime':1323630836,
#		'ctime':1323630836,
#		'mtime':1323630836,
#		'indirect':0,
#		'location':2444
#		}
#
#
#
#
#
FILEPREFIX = 'linddata.'
ROOTDIRECTORYINODE = 26
superBlock = {'creationTime':1376483073,
		'mounted':0,
		'devId':20,
		'freeStart':1,
		'freeEnd':25,
		'root':26,
		'maxBlocks':10000
        }
# store the free numbers of each block which store free block number
FREEBLOCKNUMBERS = []

fastInodeLookUpTable = {}
fileDescriptorTable = {}
fileObjectTable = {}
rootDirInfo = {}

# lock
filesystemlock = createlock()

# current working directory is '/'
fs_calls_context = {}
fs_calls_context['currentworkingdirectory'] = '/'

#some limits
fs_calls_context['blocksize'] = 4096
fs_calls_context['maxsize'] = 1638400
fs_calls_context['maxblocknumber'] = 10000
fs_calls_context['totalfreeblock'] = 0

SILENT = True

def warning(*msg):
    if not SILENT:
        for part in msgL:
            print part,
        print

class SyscallError(Exception):
    ''' a system error '''

class UnimplementedError(Exception):
    ''' a system error '''

############### load ####################
def load_fs():
    try:
        for i in range(0,10000):
            openfile(FILEPREFIX+str(i),False).close()
    except FileNotFoundError,e:
        warning("Note: No filesystem found, building a fresh one")
        _blank_fs_init()
    else:
        # restore
        restore_data()

############### init ####################
def _blank_fs_init():
    for filename in listfiles():
        if filename.startswith(FILEPREFIX):
            removefile(filename)

    for i in range(0,10000):
        fileName=FILEPREFIX+str(i)
        f=openfile(fileName,True)
        f.writeat('\x00'*4096,0)
        f.close()

    # persist superBlock
    persist_data(superBlock,0)

    # store free blocks into linddata.1 to linddata.25
    firstFreeBlockList = range(27,400)
    persist_data(firstFreeBlockList,1)

    for j in range(2,26):
        freeBlockList = range(400*(j-1),400*j)
        persist_data(freeBlockList,j)

    # store rootDirInfo into linddata.26
    rootDirInfo['size'] = 0
    rootDirInfo['uid'] = DEFAULT_UID
    rootDirInfo['gid'] = DEFAULT_GID
    rootDirInfo['mode'] = S_IFDIR | S_IRWXA
    rootDirInfo['atime'] = 1323630836
    rootDirInfo['ctime'] = 1323630836
    rootDirInfo['mtime'] = 1323630836
    rootDirInfo['linkcount'] = 2
    rootDirInfo['filename_to_inode_dict'] = {'.': ROOTDIRECTORYINODE,
                                            '..': ROOTDIRECTORYINODE}

    persist_data(rootDirInfo,26)

    # freeBlocks is 10000-27
    fs_calls_context['totalfreeblock'] = 9973

    fastInodeLookUpTable['/'] = ROOTDIRECTORYINODE

# store data into a block
def persist_data(ListOrDict,fileNumber):
    persistData = serializedata(ListOrDict)
    persistFile = openfile(FILEPREFIX+str(fileNumber),True)
    persistData += '\x00'* (4096-len(persistData))
    persistFile.writeat(persistData,0)
    persistFile.close()

# get data needed in a block
def fetch_data(fileNumber):
    fetchFile = openfile(FILEPREFIX+str(fileNumber),True)
    fetchData = fetchFile.readat(None,0)
    fetchFile.close()
    fetchDataList = list(fetchData)
    fetchDataList = [i for i in fetchDataList if i!='\x00']
    fetchData = "".join(fetchDataList)
    fetchDataDeserialized = deserializedata(fetchData)
    return fetchDataDeserialized

def restore_data():
    rootFileDataDeserialized = fetch_data(0)
    rootFileDataDeserialized['mounted'] += 1
    persist_data(rootFileDataDeserialized,0)

    #count free blocks left
    fs_calls_context['totalfreeblock'] = _search_free_blocks()

    #need to rebuild the fastInodeLookUpTable
    _rebuild_fastinodelookuptable()

def _recursive_rebuild_fastinodelookuptable(path,inodeNumber):
    inodeDict = fetch_data(inodeNumber)
    if 'filename_to_inode_dict' in inodeDict:
        for entryname in inodeDict['filename_to_inode_dict']:
            if entryname == '.' or '..':
                continue
	    entryinode = inodeDict['filename_to_inode_dict'][entryname]
            entrypurepathname = _get_absolute_path(path+'/'+entryname[1:])
            fastInodeLookUpTable[entrypurepathname] = entryinode
            if entryname[0] == 'd':
                _recursive_rebuild_fastinodelookuptable(entrypurepathname,entryinode)

def _rebuild_fastinodelookuptable():
    for item in fastInodeLookUpTable:
        del fastInodeLookUpTable[item]

    fastInodeLookUpTable['/'] = ROOTDIRECTORYINODE

    _recursive_rebuild_fastinodelookuptable('/',ROOTDIRECTORYINODE)


#################   helper function part   ##############
# to search free blocks in linddata.1 to linddata.25
def _search_free_blocks():
    freeBlocksNumber = 0
    for i in range(1,26):
        freeBlocksData = fetch_data(i)
        FREEBLOCKNUMBERS.append(len(freeBlocksData))
        freeBlocksNumber += len(freeBlocksData)
    return freeBlocksNumber

# if a dir block is needed, then numberNeeded is 1
# if a file whose size is less than block size, then numberNeeded is 2
# if a file whose size exceeds block size, then numberNeeded is at least 4
# return a list contains all the block numbers that has been allocated, and delete these block
# numbers from freeBlock blocks
# will be used when writing files or mkdir
def _allocate_for_need(numberNeeded):
    restNumberNeeded = numberNeeded
    blocksNumberAllocated = []
    if fs_calls_context['totalfreeblock'] < numberNeeded:
        warning("Not enough free blocks for this file.")
    else:
        for i in range(1,26):
            if FREEBLOCKNUMBERS[i] == 0:
                continue
            elif FREEBLOCKNUMBERS[i] < restNumberNeeded:
                f = openfile(PREFIX+str(i),True)
                fData = f.readat(None,0)
                freeBlocksData = deserializedata(fData)
                while freeBlocksData:
                    blocksNumberAllocated.append(freeBlocksData.pop(0))
                fData = serializedata(freeBlocksData)
                f.writeat(fData,0)
                f.close()
                restNumberNeeded -= FREEBLOCKNUMBERS[i]
                fs_calls_context['totalfreeblock'] -= FREEBLOCKNUMBERS[i]
                FREEBLOCKNUMBERS[i] = 0

            else:
                f = openfile(PREFIX+str(i),True)
                fData = f.readat(None,0)
                freeBlocksData = deserializedata(fData)
                for j in range(0,restNumberNeeded):
                    blocksNumberAllocated.append(freeBlocksData.pop(0))
                fData = serializedata(freeBlocksData)
                f.writeat(fData,0)
                f.close()
                FREEBLOCKNUMBERS[i] -= restNumberNeeded
                fs_calls_context['totalfreeblock'] -= restNumberNeeded
    return blocksNumberAllocated

# find blocks used by a dir or file need to be delete
def find_used_block(path):
    truepath = _get_absolute_path(path)
    thisinode = fastInodeLookUpTable[truepath]
    thisinodeInfo = fetch_data(thisinode)
    if IS_DIR(thisinodeInfo['mode']):
        blockList=[thisinode]
        return blockList
    elif thisinodeInfo['indirect']==0:
        blockList=[thisinode]
        blockList.append(thisinodeInfo['location'])
        return blockList
    else:
        blockList=[thisinode]
        blockList.append(thisinodeInfo['location'])
        indexList = fetch_data(thisinodeInfo['location'])
        blockList = blockList + indexList
        return blockList

# recycle blocks into free block list
def recycle_block(recycleBlockList):
    if recycleBlockList:
        for item in recycleBlockList:
            fs_calls_context['totalfreeblock'] += 1
            i = item/400+1
            FREEBLOCKNUMBERS[i] += 1
            blockList = fetch_data(i)
            blockList.append(item)
            persist_data(blockList,i)

# still need to be changed because of dir prefix
def _get_absolute_path(path):
    if path == '':
        return path

    if path[0] != '/':
        path = fs_calls_context['currentworkingdirectory'] + '/' + path

    pathlist = path.split('/')

    assert(pathlist[0] == '')
    pathlist = pathlist[1:]

    while True:
        try:
            pathlist.remove('.')
        except ValueError:
            break

    while True:
        try:
            pathlist.remove('')
        except ValueError:
            break

    position = 0
    while position < len(pathlist):
        if pathlist[position] == '..':
            if position > 0:
                del pathlist[position]
                del pathlist[position-1]

                position = position - 1
                continue
            else:
                position = position + 1
    return '/'+'/'.join(pathlist)

def _get_absolute_parent_path(path):
    return _get_absolute_path(path+'/..')

############################ syscall ##############################
def _istatfs_helper(inode):
    fsData = fetch_data(inode)
    return fsData

def fstatfs_syscall(fd):
    return 0

def statfs_syscall(path):
    filesystemlock.acquire(True)
    try:
        truepath = _get_absolute_path(path)

        if truepath not in fastInodeLookUpTable:
            raise SyscallError("statfs_syscall","ENOENT","The path does not exist.")
        thisinode = fastInodeLookUpTable[truepath]

        return _istatfs_helper(thisinode)

    finally:
        filesystemlock.release()

def access_syscall(path, amode):
    filesystemlock.acquire(True)
    try:
        truepath = _get_absolute_path(path)
        if truepath not in fastInodeLookUpTable:
            raise SyscallError("access_syscall","ENOENT","A directory in the path does not exist or file not found.")
        thisinode = fastInodeLookUpTable[truepath]

        inodeData = fetch_data(thisinode)
        if inodeData['mode'] & amode == amode:
            return 0
        raise SyscallError("access_syscall","EACESS","The requested access is denied.")
    finally:
        filesystemlock.release()

def chdir_syscall(path):
    truepath = _get_absolute_path(path)

    if truepath not in fastInodeLookUpTable:
        raise SyscallError("chdir_syscall","ENOENT","A directory in the path does not exist.")
    fs_calls_context['currentworkingdirectory'] = truepath

    return 0

def mkdir_syscall(path,mode):
    filesystemlock.acquire(True)
    try:
        if path == '':
            raise SyscallError("mkdir_syscall","ENOENT","Path does not exist.")

        truepath = _get_absolute_path(path)

        if truepath in fastInodeLookUpTable:
            raise SyscallError("mkdir_syscall","EEXIST","The path exists.")

        trueparentpath = _get_absolute_parent_path(path)

        if trueparentpath not in fastInodeLookUpTable:
            raise SyscallError("mkdir_syscall","ENOENT","Path does not exist.")

        parentinode = fastInodeLookUpTable[trueparentpath]
        parentinodeDict = fetch_data(parentinode)

        if not IS_DIR(parentinodeDict['mode']):
            raise SyscallError("mkdir_syscall","ENOTDIR","Path's parent is not a directory.")

        dirname = 'd'+truepath.split('/')[-1]
        newinodeBlock = _allocate_for_need(1)[0]
        parentinodeDict['filename_to_inode_dict'][dirname] = newinodeBlock
        parentinodeDict['linkcount'] += 1
        persist_data(parentinodeDict,parentinode)
        newDirInfo = {'size':1033,
		    'uid':1000,
		    'gid':1000,
		    'mode':S_IFDIR | S_IRWXA,
		    'atime':1323630836,
    	    'ctime':1323630836,
		    'mtime':1323630836,
		    'linkcount':2,
		    'filename_to_inode_dict':{'d.':newinodeBlock,
						'd..':parentinode,
                        }
            }
        persist_data(newDirInfo,newinodeBlock)
        fastInodeLookUpTable['truepath'] = newinodeBlock

        return 0

    finally:
        filesystemlock.release()

def rmdir_syscall(path):
    filesystemlock.acquire(True)
    try:
        truepath = _get_absolute_path(path)

        # Is it the root?
        if truepath == '/':
            raise SyscallError("rmdir_syscall","EINVAL","Cannot remove the root directory.")

        # is the path there?
        if truepath not in fastInodeLookUpTable:
            raise SyscallError("rmdir_syscall","EEXIST","The path does not exist.")

        thisinode = fastInodeLookUpTable[truepath]
        thisinodeInfo = fetch_data(thisinode)

        # okay, is it a directory?
        if not IS_DIR(thisinodeInfo['mode']):
            raise SyscallError("rmdir_syscall","ENOTDIR","Path is not a directory.")

        # Is it empty?
        if thisinodeData['linkcount'] > 2:
            raise SyscallError("rmdir_syscall","ENOTEMPTY","Path is not empty.")

        trueparentpath = _get_absolute_parent_path(path)
        parentinode = fastInodeLookUpTable[trueparentpath]
        parentinodeInfo = fetch_data(parentinode)
        recycleBlockList = [thisinode]

        recycle_block(recycleBlockList)

        # We're ready to go!   Let's clean up the file entry
        dirname = 'd'+truepath.split('/')[-1]

        del parentinodeInfo['filename_to_inode_dict'][dirname]
        # remove the entry from the parent...

        # decrement the link count on the dir...
        parentinodeInfo['linkcount'] -= 1
        persist_data(parentinodeInfo,parentinode)
        # finally, clean up the fastinodelookuptable and return success!!!
        del fastInodeLookUpTable[truepath]

        return 0

    finally:
        filesystemmetadatalock.release()

def link_syscall(oldpath,newpath):
    filesystemlock.acquire(True)
    try:
        trueOldPath = _get_absolute_path(oldpath)

        if trueOldPath not in fastInodeLookUpTable:
            raise SyscallError("link_syscall","ENOENT","Old path does not exist.")
        oldinode = fastInodeLookUpTable[trueOldPath]
        oldinodeInfo = fetch_data(oldinode)
        if IS_DIR(oldinodeInfo['mode']):
            raise SyscallError("link_syscall","EPERM","Old path is a directory.")

        if newpath == '':
            raise SyscallError("link_syscall","ENOENT","New path does not exist.")
        trueNewPath = _get_absolute_path(newpath)

        if trueNewPath in fastInodeLookUpTable:
            raise SyscallError("link_syscall","EEXIST","newpath already exists.")

        trueNewParentPath = _get_absolute_parent_path(newpath)

        if trueNewParentPath not in fastInodeLookUpTable:
            raise SyscallError("link_syscall","ENOENT","New path does not exist.")
        newParentInode = fastInodeLookUpTable[trueNewParentPath]
        trueNewParentPathInfo = fetch_data(newParentInode)

        if not IS_DIR(trueNewParentPathInfo['mode']):
            raise SyscallError("link_syscall","ENOTDIR","New path's parent is not a directory.")

        newFileName = 'f'+trueNewPath.split('/')[-1]

        trueNewParentPathInfo['filename_to_inode_dict'][newFileName] = oldinode
        trueNewParentPathInfo['linkcount'] += 1
        persist_data(trueNewParentPathInfo, newParentInode)

        oldinodeInfo['linkcount'] += 1
        persist_data(oldinodeInfo, oldinode)

        fastInodeLookUpTable[trueNewPath] = oldinode

        return 0
    finally:
        filesystemlock.release()

def unlink_syscall():
    filesystemlock.acquire(True)
    try:
        truepath = _get_absolute_path(path)
        if truepath not in fastInodeLookUpTable:
            raise SyscallError("unlink_syscall","ENOENT","The path does not exist.")
            thisinode = fastInodeLookUpTablep[truepath]
            thisinodeInfo = fetch_data(thisinode)
            if IS_DIR(thisinodeInfo['mode']):
                raise SyscallError("unlink_syscall","EISDIR","Path is a directory.")

            trueparentpath = _get_absolute_parent_path(path)
            parentinode = fastInodeLookUpTable[trueparentpath]
            parentinodeInfo = fetch_data(parentinode)

            dirname = 'f'+truepath.split('/')[-1]
            del parentinodeInfo['filename_to_inode_dict'][dirname]
            parentinodeInfo['linkcount'] -= 1
            persist_data(parentinodeInfo,parentinode)
            del fastInodeLookUpTable[truepath]
            thisinodeInfo['linkcount'] -= 1
            if thisinodeInfo['linkcount'] == 0:
                recycle_block(find_used_block(truepath))
            else:
                persist_data(thisinodeInfo, thisinode)

        return 0
    finally:
        filesystemlock.release()

def open_syscall(path, flags, mode):
    filesystemlock.acquire(True)
    try:
        if path == '':
            raise SyscallError("open_syscall","ENOENT","The file does not exist.")

        truepath = _get_absolute_path(path)

        # is the file missing?
        if truepath not in fastInodeLookUpTable:

            # did they use O_CREAT?
            if not O_CREAT & flags:
                raise SyscallError("open_syscall","ENOENT","The file does not exist.")

            # okay, it doesn't exist (great!).   Does it's parent exist and is it a
            # dir?
            trueparentpath = _get_absolute_parent_path(path)

            if trueparentpath not in fastInodeLookUpTable:
                raise SyscallError("open_syscall","ENOENT","Path does not exist.")

            parentinode = fastInodeLookUpTable[trueparentpath]
            parentinodeDict = fetch_data(parentinode)
            if not IS_DIR(parentinodeDict['mode']):
                raise SyscallError("open_syscall","ENOTDIR","Path's parent is not a directory.")



            # okay, great!!!   We're ready to go!   Let's make the new file...
            filename = 'f'+truepath.split('/')[-1]

            # first, make the new file's entry...
            newinodeBlock = _allocate_for_need(1)[0]
            inodeInfo={
                        'size':0,
                        'uid':1000,
                        'gid':1000,
                        'mode':33261,
                        'linkcount':1,
                        'atime':132363086,
                        'ctime':132363086,
                        'mtime':132363086,
                        'indirect':0,
                        'location':''
                    }
            persist_data(inodeInfo,newinodeBlock)

            # let's make the parent point to it...
            parentinodeDict['filename_to_inode_dict'][filename] = newinodeBlock
            # ... and increment the link count on the dir...
            parentinodeDict['linkcount'] += 1

            # finally, update the fastinodelookuptable
            fastInodeLookUpTable[truepath] = newinodeBlock

    # if the file did exist, were we told to create with exclusion?
        else:
            # did they use O_CREAT and O_EXCL?
            if O_CREAT & flags and O_EXCL & flags:
                raise SyscallError("open_syscall","EEXIST","The file exists.")

            # This file should be removed.   If O_RDONLY is set, the behavior
            # is undefined, so this is okay, I guess...
            if O_TRUNC & flags:
                inode = fastInodeLookUpTable[truepath]
                if inode in fileDescriptorTable:
                    del fileDescriptorTable[inode]
                inodeInfo = fetch_data(inode)
                if inodeInfo['indirect']==0:
                    pass
                elif inodeInfo['location']=='':
                    recycle_block([inode])
                else:
                    blockList = fetch_data(inodeInfo['location'])
                    blockList.append(inode)
                    recycle_block(blockList)
        if O_APPEND & flags:
            inode = fastInodeLookUpTable[truepath]
            inodeInfo = fetch_data(inode)
            if not IS_DIR(inodeInfo['mode']):
                if inodeInfo['indirect']==0:
                    fileObjectTable[truepath]=fetch_data(inodeInfo['location'])
                else:
                    blockList = fetch_data(inodeInfo['location'])
                    for item in blockList:
                        fileObjectTable[truepath] += fetch_data(item)
                position = inodeInfo['size']
        else:
            position = 0
        fileDesriptorTable[truepath] = {'position':position, 'lock':createlock(),'flags':flags}

        return truepath
    finally:
        filesystemlock.release()

def creat_syscall(pathname, mode):
    try:
        return open_syscall(pathname, O_CREAT | O_TRUNC | O_WRONLY, mode)
    except SyscallError, e:
        assert(e[0]=='open_syscall')

        raise SyscallError('creat_syscall',e[1],e[2])

def lseek_syscall(fd,offset,whence):
    if fd not in fileDescriptorTable:
        raise SyscallError("lseek_syscall","EBADF","Invalid file descriptor.")
    fileDescriptorTable[fd]['lock'].acquire(True)
    try:
        inode = fastInodeLookUpTable[fd]
        inodeInfo = fetch_data(inode)
        if IS_REG(inodeInfo['mode']):
            filesize = inodeInfo['size']
        else:
            raise SyscallError("lseek_syscall","EINVAL","File descriptor does not refer to a regular file or directory.")

        if whence == SEEK_SET:
            eventualpos = offset
        elif whence == SEEK_CUR:
            eventualpos = fileDescriptorTable[fd]['position']+offset
        elif whence == SEEK_END:
            eventualpos = filesize + offset
        else:
            raise SyscallError("lseek_syscall","EINVAL","Invalid whence.")
        if eventualpos < 0:
            raise SyscallError("lseek_syscall","EINVAL","Seek before position 0 in file.")
        fileDescriptorTable[fd]['position'] = eventualpos
        return eventualpos
    finally:
        fileDescriptorTable[fd]['lock'].release()


def read_syscall(fd,count):
    if fd not in fileDescriptorTable:
        raise SyscallError("read_syscall","EBADF","Invalid file descriptor.")

    fileDescriptorTable[fd]['lock'].acquire(True)

    try:
        position = fileDescriptorTable[fd]['position']
        data = fileObjectTable[fd].readat(count,position)

        fileDescriptorTable[fd]['position'] += len(data)
        return data
    finally:
        fileDescriptorTable[fd]['lock'].release()

def write_syscall(fd,data):
    if fd not in fileDescriptorTable:
        raise SyscallError("write_syscall","EBADF","Invalid file descriptor.")
    fileDescriptorTable[fd]['lock'].acquire(True)
    try:
        position = fileDescriptorTable[fd]['position']
        inode = fastInodeLookUpTable[fd]
        inodeInfo = fetch_data(inode)
        if not IS_DIR(inodeInfo['mode']):
            filesize = inodeInfo['size']
        blankbytecount = position - filesize
        if blankbytecount > 0:
            fileObjectTable[fd].append('\0'*blankbytecount)
        fileObjectTable[fd][position:]=data
        fileDescriptorTable[fd]['position'] += len(data)
        if fileDescriptorTable[fd]['position'] > filesize:
            inodeInfo['size'] = fileDescriptorTable[fd]['position']
            persist_data(inodeInfo,inode)
        return len(data)
    finally:
        fileDescriptorTable[fd]['lock'].release()

def truncate_syscall(path,length):
    truepath = open_syscall(path, O_RDWR, S_IRWXA)
    if length<0:
        raise SyscallError("truncate_syscall", "EINVAL", "Incorrect length passed.")
    elif fileDescriptorTable[truepath]['position']>=length:
        fileDescriptorTable[truepath]['position']=fileDescriptorTable[truepath]['position']-length
    else:
        fileDescriptorTable[truepath]['position']=0
    close_syscall(truepath)
    return 0

def close_syscall(fd):
    inode = fastInodeLookUpTable[fd]
    inodeInfo = fetch_data(inode)
    finalsize = len(fileObjectTable[fd])
    finalString = fileObjectTable[fd]
    inodeInfo['size'] = finalsize
    if (finalsize+4096-1)/4096 == 0:
        finalindirect = 0
        finalblockneed = 1
    elif (finalsize+4096-1)/4096 == 1:
        finalindirect = 0
        finalblockneed = 2
    else:
        finalindirect = 1
        finalblockneed = (finalsize+4096-1)/4096+2

    if inodeInfo['indirect']==0:
        if inodeInfo['location'] == '':
            curblock = [inode]
        else:
            curblock = [inode]+[inodeInfo['location']]
    else:
        curblock = [inode]+[inodeInfo['location']]+fetch_data(inodeInfo['location'])
    if finalblockneed == 1:
        recycle_block(curblock[finalblockneed:])
        finalblock = curblock[0:finalblockneed]
        inodeInfo['indirect']=0
        inodeInfo['location']=''
        inodeInfoBlockNumber = curblock[0]
    elif finalblockneed ==2:
        if len(curblock) >= finalblockneed:
            recycle_block(curblock[finalblockneed:])
            finalblock = curblock[0:2]
            inodeInfo['indirect']=0
            inodeInfo['location']=curblock[1]
            inodeInfoBlockNumber = curblock[0]
            dataBlock = inodeInfo['location']
            persist(finalString,dataBlock)
        else:
            inodeInfo['indirect']=0
            inodeInfo['location']=_allocate_for_need(1)[0]
            inodeInfoBlockNumber = curblock[0]
            dataBlock = inodeInfo['location']
            persist(finalString,dataBlock)
    else:
        if len(curblock)>=finalblockneed:
            recycle_block(curblock[finalblockneed:])
            finalblock = curblock[0:finalblockneed]
            inodeInfo['indirect']=1
            inodeInfoBlockNumber = curblock[0]
            inodeInfo['location']=curblock[1]
            dataBlock = curblock[2:finalblockneed]
            indexBlockNumber = inodeInfo['location']
            persist(dataBlock,indexBlockNumber)
            for item in dataBlock:
                persist(finalString[:4096],item)
                finalString = finalString[4096:]
        else:
            inodeInfo['indirect'] = 1
            if len(curblock)==1:
                inodeInfoBlockNumber = curblock[0]
                allocatedBlock = _allocate_for_need(finalblockneed-len(curblock))
                inodeInfo['location'] = allocatedBlock.pop(0)
                indexBlockNumber = inodeInfo['location']
                dataBlock = allocatedBlock
                persist(dataBlock,indexBlockNumber)
                for item in dataBlock:
                    persist(finalString[:4096],item)
                    finalString = finalString[4096:]
            else:
                inodeInfoBlockNumber = curblock[0]
                allocatedBlock = _allocate_for_need(finalblockneed-len(curblock))
                inodeInfo['location'] = curblock[1]
                indexBlockNumber = inodeInfo['location']
                dataBlock = curblock[2:]+allocatedBlock
                persist(dataBlock,indexBlockNumber)
                for item in dataBlock:
                    persist(finalString[:4096],item)
                    finalString = finalString[4096:]
    persist(inodeInfo,inodeInfoBlockNumber)
    del fileObjectTable[fd]
    return 0

def rename_syscall(old,new):
    filesystemlock.acquire(True)
    try:
        true_old_path = _get_absolute_path(old)
        true_new_path = _get_absolute_path(new)

        if true_old_path not in fastInodeLookUpTable:
            raise SyscallError("rename_syscall", "ENOENT", "Old file does not exist")
        if true_new_path == '':
            raise SyscallError("rename_syscall", "ENOENT", "New file does not exist")

        trueparentpath_old = _get_absolute_parent_path(true_old_path)
        parentinode = fastInodeLookUpTable[trueparentpath_old]
        parentinodeInfo = fetch_data(parentinode)
        inode = fastInodeLookUpTable[true_old_path]
        newname = 'f'+true_new_path.split('/')[-1]
        parentinodeInfo['filename_to_inode_dict'][newname] = inode
        fastInodeLookUpTable[true_new_path] = inode
        oldname = 'f'+true_old_path.split('/')[-1]
        del parentinodeInfo['filename_to_inode_dict'][oldname]
        persist_data(parentinodeInfo,parentinode)
        del fastInodeLookUpTable[true_old_path]
    finally:
        filesystemlock.release()
    return 0

def dup2_syscall(oldfd,newfd):
    return 0

def dup_syscall(fd):
    return 0

def fcntl_syscall(fd, cmd, *args):
    return 0

def getdents_syscall(fd,quantity):
    return 0

def chmod_syscall(path, mode):
    return 0

def ftruncate_syscall(fd, new_len):
    return 0

def mknod_syscall(path, mode, dev):
    return 0

def getuid_syscall():
    return 0

def geteuid_syscall():
    return 0

def getgid_syscall():
    return 0

def getegid_syscall():
    return 0

def getrlimit_syscall(res_type):
    return 0

def setrlimit_syscall(res_type,limits):
    return 0

def flock_syscall(fd,operation):
    return 0

def stat_syscall(path):
    filesystemlock.acquire(True)
    try:
        truepath = _get_absolute_path(path)
        if truepath not in fastInodeLookUpTable:
            raise SyscallError("stat_syscall","ENOENT","The path does not exist.")

        thisinode = fastInodeLookUpTable[truepath]
        thisinodeInfo = fetch_data(thisinode)
        return thisinodeInfo

    finally:
        filesystemlock.release()

def fstat_syscall(fd):
    return 0

