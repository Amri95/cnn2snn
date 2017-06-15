#coding=utf-8

import time
import os.path
import scipy
import scipy.io as sio
import cPickle as pickle
from struct import unpack
import sys
from matplotlib.pyplot import *
from dim3_ind import *
from brian2 import *
import matplotlib.pyplot as plt

start_scope()

# specify the location of the MNIST data
MNIST_data_path = '../mnist/'

#------------------------------------------------------------------------------ 
# functions
#------------------------------------------------------------------------------     

def get_labeled_data(picklename, bTrain = True):
    """Read input-vector (image) and target class (label, 0-9) and return
       it as list of tuples.
    """
    if os.path.isfile('%s.pickle' % picklename):
        data = pickle.load(open('%s.pickle' % picklename))
    else:
        # Open the images with gzip in read binary mode
        if bTrain:
            images = open(MNIST_data_path + 'train-images-idx3-ubyte','rb')
            labels = open(MNIST_data_path + 'train-labels-idx1-ubyte','rb')
        else:
            images = open(MNIST_data_path + 't10k-images-idx3-ubyte','rb')
            labels = open(MNIST_data_path + 't10k-labels-idx1-ubyte','rb')

        # Get metadata for images
        images.read(4)  # skip the magic_number
        number_of_images = unpack('>I', images.read(4))[0]
        rows = unpack('>I', images.read(4))[0]
        cols = unpack('>I', images.read(4))[0]
        # Get metadata for labels
        labels.read(4)  # skip the magic_number
        N = unpack('>I', labels.read(4))[0]
    
        if number_of_images != N:
            raise Exception('number of labels did not match the number of images')
        # Get the data
        x = np.zeros((N, rows, cols), dtype=np.uint8)  # Initialize numpy array
        y = np.zeros((N, 1), dtype=np.uint8)  # Initialize numpy array
        for i in xrange(N):
            x[i] = [[unpack('>B', images.read(1))[0] for unused_col in xrange(cols)]  for unused_row in xrange(rows) ]
            y[i] = unpack('>B', labels.read(1))[0]
            
        data = {'x': x, 'y': y, 'rows': rows, 'cols': cols}
        pickle.dump(data, open("%s.pickle" % picklename, "wb"))
    return data

def create_conv_connections(in_ind, out_ind, output_size, kernel_num, kernel_size, kernel_weights, pre_ind, post_ind, conv_w):
    for h in range(output_size):    # output height
        for w in range(output_size):    # output width
            for k in range(kernel_num):     # kernel numbers
                for kd in range(in_ind.sz0):    # kernel depth
                    for kh in range(kernel_size):   # kernel height
                        for kw in range(kernel_size):   # kernel width
                            i = in_ind.ind3 (kh + h, kw + w, kd)
                            j = out_ind.ind3(     h,      w, k )
                            pre_ind.append(i)
                            post_ind.append(j)
                            conv_w.append(kernel_weights[kh, kw, kd, k])
    
def create_max_pooling_inter_connections(inter_ind, output_size, kernel_num, kernel_size, kernel_stride, pre_ind, post_ind, pool_w):
    for h in range(output_size):
        for w in range(output_size):
            for k in range(kernel_num):
                for kh1 in range(kernel_size):
                    for kw1 in range(kernel_size):
                        for kh2 in range(kernel_size):
                            for kw2 in range(kernel_size):
                                if (kh2 == kh1) and (kw2 == kw1):
                                    continue
                                i = inter_ind.ind3(kh1 + kernel_stride*h, kw1 + kernel_stride*w, k)
                                j = inter_ind.ind3(kh2 + kernel_stride*h, kw2 + kernel_stride*w, k)
                                pre_ind.append(i)
                                post_ind.append(j)
                                pool_w.append(-1)

def create_max_pooling_out_connections(in_ind, out_ind, output_size, kernel_num, kernel_size, kernel_stride, pre_ind, post_ind, pool_w):
    for h in range(output_size):
        for w in range(output_size):
            for k in range(kernel_num):
                for kh in range(kernel_size):
                    for kw in range(kernel_size):
                        i = in_ind.ind3 (kh + kernel_stride*h, kw + kernel_stride*w, k)
                        j = out_ind.ind3(                   h,                    w, k)
                        pre_ind.append(i)
                        post_ind.append(j)
                        pool_w.append(1)

def create_ip_connections(in_ind, output_n, ip_weights, pre_ind, post_ind, ip_w):
    for n in range(output_n):
        for h in range(in_ind.sz2):
            for w in range(in_ind.sz1):
                for d in range(in_ind.sz0):
                    i = in_ind.ind3(h, w, d)
                    pre_ind.append(i)
                    post_ind.append(n)
                    ip_w.append(ip_weights[i, n])

#------------------------------------------------------------------------------ 
# load MNIST
#------------------------------------------------------------------------------
# start = time.time()
# training = get_labeled_data('cache/training')
# end = time.time()
# print 'time needed to load training set:', end - start
 
start = time.time()
testing = get_labeled_data('cache/testing', bTrain = False)
end = time.time()
print 'time needed to load test set:', end - start

#------------------------------------------------------------------------------ 
# set parameters and equations
#------------------------------------------------------------------------------
eqs_input           = '''rates     : Hz
                         dv/dt = 1 : second'''
input_thresh        = 'v > 1/rates'
input_reset         = 'v -= 1/rates'

eqs_conv1           = 'v : 1'
eqs_pool1           = 'v : 1'
eqs_conv2           = 'v : 1'
eqs_pool2           = 'v : 1'
eqs_ip1             = 'v : 1'
eqs_ip2             = 'v : 1'

conv1_thresh        = 'v >= 1'
conv1_reset         = 'v = 0'

pool1_thresh        = 'v >= 1'
pool1_reset         = 'v = 0'

conv2_thresh        = 'v >= 1'
conv2_reset         = 'v = 0'

pool2_thresh        = 'v >= 1'
pool2_reset         = 'v = 0'

ip1_thresh          = 'v >= 1'
ip1_reset           = 'v = 0'

ip2_thresh          = 'v >= 1'
ip2_reset           = 'v = 0'

input_size          = 28
input_n             = input_size * input_size
input_ind           = dim3_ind(input_size, input_size, 1)

conv1_kernel_size   = 5
conv1_kernel_num    = 20
conv1_kernel_stride = 1
conv1_output_size   = (input_size - conv1_kernel_size + 0) / conv1_kernel_stride + 1    # should be 24
conv1_output_n      = conv1_output_size * conv1_output_size
conv1_ind           = dim3_ind(conv1_output_size, conv1_output_size, conv1_kernel_num)

pool1_kernel_size   = 2
pool1_kernel_num    = conv1_kernel_num
pool1_kernel_stride = 2
pool1_output_size   = conv1_output_size / 2     # should be 12
pool1_output_n      = pool1_output_size * pool1_output_size
pool1_ind           = dim3_ind(pool1_output_size, pool1_output_size, pool1_kernel_num)

conv2_kernel_size   = 5
conv2_kernel_num    = 50
conv2_kernel_stride = 1
conv2_output_size   = (pool1_output_size - conv2_kernel_size + 0) / conv2_kernel_stride + 1    # should be 8
conv2_output_n      = conv2_output_size * conv2_output_size
conv2_ind           = dim3_ind(conv2_output_size, conv2_output_size, conv2_kernel_num)

pool2_kernel_size   = 2
pool2_kernel_num    = conv2_kernel_num
pool2_kernel_stride = 2
pool2_output_size   = conv2_output_size / 2     # should be 4
pool2_output_n      = pool2_output_size * pool2_output_size
pool2_ind           = dim3_ind(pool2_output_size, pool2_output_size, pool2_kernel_num)

ip1_output_n        = 500
ip1_ind             = dim3_ind(1, 1, ip1_output_n)
ip2_output_n        = 10
ip2_ind             = dim3_ind(1, 1, ip2_output_n)

#------------------------------------------------------------------------------ 
# load synapses weights from pretrained model
#------------------------------------------------------------------------------
pretrained_lenet = sio.loadmat('../tensorflow/output/weights/lenet_max_pooling.mat')
conv1_weights    = pretrained_lenet['conv1_weights']
conv2_weights    = pretrained_lenet['conv2_weights'] * 0.5
ip1_weights      = pretrained_lenet['ip1_weights']   * 0.5
ip2_weights      = pretrained_lenet['ip2_weights']

#------------------------------------------------------------------------------ 
# create network population and synapses
#------------------------------------------------------------------------------

# input group
input_group = NeuronGroup(input_n, eqs_input, threshold = input_thresh, reset = input_reset, method = 'euler')

# conv1 group
conv1_group  = NeuronGroup(conv1_output_n * conv1_kernel_num, eqs_conv1, threshold = conv1_thresh, reset = conv1_reset, method = 'euler')
synapses_input_conv1 = Synapses(input_group, conv1_group, model='w:1', on_pre = 'v_post += w', method = 'linear')   # on_pre = 'v_post = clip(v_post+w, 0, 1)'
pre_ind  = []
post_ind = []
conv_w  = []
create_conv_connections(input_ind, conv1_ind, conv1_output_size, conv1_kernel_num, conv1_kernel_size, conv1_weights, pre_ind, post_ind, conv_w)
synapses_input_conv1.connect(i = pre_ind, j = post_ind)
synapses_input_conv1.w = conv_w;

# pool1 intermediate group
synapses_conv1_conv1 = Synapses(conv1_group, conv1_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
pool_w   = []
create_max_pooling_inter_connections(conv1_ind, pool1_output_size, pool1_kernel_num, pool1_kernel_size, pool1_kernel_stride, pre_ind, post_ind, pool_w)
synapses_conv1_conv1.connect(i = pre_ind, j = post_ind)
synapses_conv1_conv1.w = pool_w;

# pool1 out group
pool1_group = NeuronGroup(pool1_output_n * pool1_kernel_num, eqs_pool1, threshold = pool1_thresh, reset = pool1_reset, method = 'euler')
synapses_conv1_pool1 = Synapses(conv1_group, pool1_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
pool_w   = []
create_max_pooling_out_connections(conv1_ind, pool1_ind, pool1_output_size, pool1_kernel_num, pool1_kernel_size, pool1_kernel_stride, pre_ind, post_ind, pool_w)
synapses_conv1_pool1.connect(i = pre_ind, j = post_ind)
synapses_conv1_pool1.w = pool_w;

# conv2 group
conv2_group  = NeuronGroup(conv2_output_n * conv2_kernel_num, eqs_conv2, threshold = conv2_thresh, reset = conv2_reset, method = 'euler')
synapses_pool1_conv2 = Synapses(pool1_group, conv2_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
conv_w   = []
create_conv_connections(pool1_ind, conv2_ind, conv2_output_size, conv2_kernel_num, conv2_kernel_size, conv2_weights, pre_ind, post_ind, conv_w)
synapses_pool1_conv2.connect(i = pre_ind, j = post_ind)
synapses_pool1_conv2.w = conv_w;

# pool2 intermediate group
synapses_conv2_conv2 = Synapses(conv2_group, conv2_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
pool_w   = []
create_max_pooling_inter_connections(conv2_ind, pool2_output_size, pool2_kernel_num, pool2_kernel_size, pool2_kernel_stride, pre_ind, post_ind, pool_w)
synapses_conv2_conv2.connect(i = pre_ind, j = post_ind)
synapses_conv2_conv2.w = pool_w;

# pool2 out group
pool2_group = NeuronGroup(pool2_output_n * pool2_kernel_num, eqs_pool2, threshold = pool2_thresh, reset = pool2_reset, method = 'euler')
synapses_conv2_pool2 = Synapses(conv2_group, pool2_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
pool_w   = []
create_max_pooling_out_connections(conv2_ind, pool2_ind, pool2_output_size, pool2_kernel_num, pool2_kernel_size, pool2_kernel_stride, pre_ind, post_ind, pool_w)
synapses_conv2_pool2.connect(i = pre_ind, j = post_ind)
synapses_conv2_pool2.w = pool_w;

# ip1 group
ip1_group = NeuronGroup(ip1_output_n, eqs_ip1, threshold = ip1_thresh, reset = ip1_reset, method = 'euler')
synapses_pool2_ip1 = Synapses(pool2_group, ip1_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
ip_w     = []
create_ip_connections(pool2_ind, ip1_output_n, ip1_weights, pre_ind, post_ind, ip_w)
synapses_pool2_ip1.connect(i = pre_ind, j = post_ind)
synapses_pool2_ip1.w = ip_w;

# ip2 group
ip2_group = NeuronGroup(ip2_output_n, eqs_ip2, threshold = ip2_thresh, reset = ip2_reset, method = 'euler')
synapses_ip1_ip2 = Synapses(ip1_group, ip2_group, model='w:1', on_pre = 'v_post += w', method = 'linear')
pre_ind  = []
post_ind = []
ip_w     = []
create_ip_connections(ip1_ind, ip2_output_n, ip2_weights, pre_ind, post_ind, ip_w)
synapses_ip1_ip2.connect(i = pre_ind, j = post_ind)
synapses_ip1_ip2.w = ip_w;


def app_run(test_start = 0, test_end = -1):
    #------------------------------------------------------------------------------ 
    # create monitors
    #------------------------------------------------------------------------------
    ip2_mon = SpikeMonitor(ip2_group)
    last_ip2_counts = np.array(ip2_mon.count)
    # ip2_counts_record = np.zeros((np.size(testing['x'], 0), 10))
    
    # conv1_mon = SpikeMonitor(conv1_group)
    # last_conv1_counts = np.array(conv1_mon.count)
    # conv1_counts_record = np.zeros((np.size(testing['x'], 0), 11520))
    
    
    #------------------------------------------------------------------------------ 
    # run the simulation and set inputs
    #------------------------------------------------------------------------------
    start = time.time()
    
    defaultclock.dt = 0.1 * ms;
    
    if test_end < test_start:
        test_num = np.size(testing['x'], 0)
        test_start = 0
        test_end = test_num
        test_range = range(test_num)
    else:
        test_num = test_end - test_start
        test_range = range(test_start, test_end)
    
    test_count = 0.0
    test_right = 0.0
    
    for i in test_range:
        input_group.rates = testing['x'][i, :, :].reshape(input_n) * Hz
        input_group.v = 0
        conv1_group.v = 0
        pool1_group.v = 0
        conv2_group.v = 0
        pool2_group.v = 0
        ip1_group.v = 0
        ip2_group.v = 0
        run(200 * ms)
        
        
        curr_ip2_counts = np.array(ip2_mon.count) - last_ip2_counts
        last_ip2_counts = np.array(ip2_mon.count)
    #     ip2_counts_record[i, :] = curr_ip2_counts
        
    #     curr_conv1_counts = np.array(conv1_mon.count) - last_conv1_counts
    #     last_conv1_counts = np.array(conv1_mon.count)
    #     conv1_counts_record[i, :] = curr_conv1_counts
    
        pred = np.argmax(curr_ip2_counts)
        label = testing['y'][i]
        if pred == label:
            test_right += 1
        test_count += 1
        
    #     print curr_ip2_counts
        
        print('%d / [%d, %d]:%f %d %d' % (i, test_start, test_end-1, test_right / test_count, test_right, test_count))
    
    end = time.time()
    print 'time needed to run simulation:', end - start



#------------------------------------------------------------------------------ 
# plot results
#------------------------------------------------------------------------------   
# print ip2_mon.count

# save classified results
# sio.savemat('output/max_pooing_it_counts.mat', {'it_counts':ip2_counts_record})

# sio.savemat('output/conv1_counts.mat', {'conv1_counts':conv1_counts_record})

if __name__ == "__main__":
    if len(sys.argv) == 3:
        app_run(int(sys.argv[1]), int(sys.argv[2]))
    else:
        app_run()
    
