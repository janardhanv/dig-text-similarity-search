from typing import List
from .base_index_handler import *


class DeployIVF(BaseIndex):
    """
    For deploying on-disk index made with DiskBuilderIVF

    :param nprobe: Number of clusters to visit during search
        (speed accuracy trade-off)
    """
    def __init__(self, path_to_deployable_index, nprobe: int = 32):
        BaseIndex.__init__(self)
        self.index = faiss.read_index(path_to_deployable_index)
        self.index.nprobe = nprobe

    def index_embeddings(self, embeddings: np.array, faiss_ids: np.array):
        # self.index.add_with_ids(embeddings, faiss_ids)
        print('Use the DiskBuilderIVF class for adding to index')


class DiskBuilderIVF(BaseIndex):
    """
    For building IVF index on-disk.
    Requires a pre-trained, empty index.
    """
    def __init__(self, path_to_empty_index):
        BaseIndex.__init__(self)
        self.path_to_empty_index = path_to_empty_index
        self.invlist_paths = list()

    def index_embeddings(self, embeddings: np.array, faiss_ids: np.array):
        self.index.add_with_ids(embeddings, faiss_ids)

    def load_empty(self):
        empty_index = faiss.read_index(self.path_to_empty_index)
        if empty_index.is_trained and empty_index.ntotal == 0:
            self.index = empty_index
        else:
            raise Exception('Index must be empty and pre-trained.\n'
                            ' index.ntotal: ({}), index.is_trained: ({})'
                            ''.format(empty_index.ntotal, empty_index.is_trained))

    def generate_invlist(self, invlist_path, faiss_ids,
                         embeddings: np.array) -> np.array:
        self.load_empty()
        self.index_embeddings(embeddings, faiss_ids)
        self.invlist_paths.append(invlist_path)
        self.save_index(invlist_path)
        self.index = None

    def n_invlists(self):
        print('* n invlists: {}'.format(len(self.invlist_paths)))

    def extend_invlist_paths(self, paths_to_add: List[str]):
        self.invlist_paths.extend(paths_to_add)
        self.n_invlists()

    def build_disk_index(self, merged_ivfs_path, merged_index_path) -> int:
        ivfs = list()
        for i, invlpth in enumerate(self.invlist_paths):
            index = faiss.read_index(invlpth, faiss.IO_FLAG_MMAP)
            ivfs.append(index.invlists)
            index.own_invlists = False      # Prevents de-allocation
            del index

        self.load_empty()
        invlists = faiss.OnDiskInvertedLists(self.index.nlist,
                                             self.index.code_size,
                                             merged_ivfs_path)

        ivf_vector = faiss.InvertedListsPtrVector()
        for ivf in ivfs:
            ivf_vector.push_back(ivf)

        ntotal = invlists.merge_from(ivf_vector.data(), ivf_vector.size())
        self.index.ntotal = ntotal
        self.index.replace_invlists(invlists)
        self.save_index(merged_index_path)
        self.index = None
        return int(ntotal)
