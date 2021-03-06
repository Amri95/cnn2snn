#coding=utf-8

# 三维索引转一维索引
# ind: 三维索引,(三维，二维，一维)
#  sz: 维度尺寸,(二维尺寸,一维尺寸)
# 返回一维索引 
class dim3_ind:
    def __init__(self, sz2, sz1, sz0):
        self.sz2 = sz2
        self.sz1 = sz1
        self.sz0 = sz0
    def ind3(self, ind2, ind1, ind0):
        assert(ind1 < self.sz1)
        assert(ind0 < self.sz0)
        return ind2 * self.sz1 * self.sz0 + ind1 * self.sz0 + ind0
    def pad_ind3(self, ind2, ind1, ind0):
        if ind1 < 0 or ind1 >= self.sz1 or ind2 < 0 or ind2 >= self.sz2:
            return -1
        else:
            assert(ind1 < self.sz1)
            assert(ind0 < self.sz0)
            return ind2 * self.sz1 * self.sz0 + ind1 * self.sz0 + ind0
    def ind2(self, ind1, ind0):
        return ind1 * self.sz0 + ind0
        