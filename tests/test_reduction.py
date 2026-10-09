import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from controller.plot import display_indices

class ReductionTests(unittest.TestCase):
    def test_narrow_peaks_and_negative_extrema_survive_reduction(self):
        values=np.zeros(10000);values[[1,4999,9998]]=[10,-10,7]
        picks=display_indices(values,600)
        self.assertTrue(set((0,1,4999,9998,9999)).issubset(picks))
        self.assertTrue(np.all(np.diff(picks)>0))
        self.assertLessEqual(len(picks),1202)
    def test_native_small_traces_keep_every_sample(self):
        self.assertTrue(np.array_equal(display_indices(np.arange(100),600),np.arange(100)))

if __name__=='__main__':unittest.main()
