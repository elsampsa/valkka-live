import os, glob, shutil
from valkka.fs import ValkkaSingleFS, ValkkaFSLoadError

class ValkkaSingleFSHandler:
    """Collection of ValkkaSingleFS instances, each one with
    identical n_blocks and blocksize

    valkkafs <-> stream id association
    """
    def __init__(self, basedir, n_blocks=None, blocksize=None):
        self.basedir=basedir
        self.n_blocks = n_blocks
        self.blocksize = blocksize
        self.fs_by_id = {}

    def wipe(self):
        for di in glob.glob(
            os.path.join(
                self.basedir,
                "valkkafs_*"
            )):
            print("ValkkaSingleFSHandler: wipe: removing", di)
            shutil.rmtree(di)

    def clear(self):
        for _id in self.fs_by_id.keys():
            path=self.getDir(_id)
            print("ValkkaSingleFSHandler: removing", path)
            # TODO

    def __str__(self):
        return "<ValkkaSingleFSHandler @ "+self.basedir+" %i filesystems>" %\
            (len(self.fs_by_id))

    def getDir(self, _id):
        return os.path.join(
            self.basedir,
            "valkkafs_%i" % (_id)
        )

    def new(self, _id):
        """Create new valkkafs corresponding to this slot
        """
        print("ValkkaSingleFSHandler: creating new valkkafs for id", _id)
        valkkafs = ValkkaSingleFS.newFromDirectory(
                dirname = self.getDir(_id),
                blocksize = self.blocksize,
                n_blocks = self.n_blocks
            )
        self.fs_by_id[_id]=valkkafs
    
    def format(self, _id):
        """stripe the device
        """
        self.fs_by_id[_id].reinit()

    def load(self, _id):
        """Try to load existing valkkafs for this slot.

        If it fails, call new
        """
        try:
            valkkafs = ValkkaSingleFS.loadFromDirectory(self.getDir(_id))
        except ValkkaFSLoadError as e:
            self.new(_id)
        else:
            self.fs_by_id[_id]=valkkafs

    def __item__(self, _id):
        return self.fs_by_id[_id]

    def tolist(self):
        return list(self.fs_by_id.values())

    def getId(self, valkkafs):
        for _id, fs in self.fs_by_id.items():
            if fs==valkkafs:
                return _id
        return None


if __name__ == "__main__":
    fs_handler = ValkkaSingleFSHandler(
        basedir = ".",
        blocksize = 1 * 1024*1024, # MB
        n_blocks = 10
    )
    fs_handler.load(1234)
    fs_handler.load(5678)
    print(fs_handler.tolist())
    
