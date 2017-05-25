import tensorflow as tf
import extract_cifar10
import time
from sys import path
import scipy.io as sio

# Parameters
isTrain = True
batch_size = 100


def weight_variable(shape, std=0.1, wd=0.004):
    initial = tf.truncated_normal(shape, stddev=std)
    weight_decay = tf.multiply(tf.nn.l2_loss(initial), wd, name='weight_loss')
    tf.add_to_collection('losses', weight_decay)
    return tf.Variable(initial)


def bias_variable(shape):
    initial = tf.constant(0.0, shape=shape)
    return tf.Variable(initial)


def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

x = tf.placeholder('float', [None, 32, 32, 3])
y_ = tf.placeholder('float', [None, 10])

# conv1
W_conv1 = weight_variable([5, 5, 3, 32], 0.0001)
b_conv1 = bias_variable([32])
conv1 = tf.nn.relu(conv2d(x, W_conv1) + b_conv1)
# pool1
pool1 = tf.nn.max_pool(
    conv1, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME', name='pool1')

# conv2
W_conv2 = weight_variable([5, 5, 32, 32], 0.01)
b_conv2 = bias_variable([32])
conv2 = tf.nn.relu(conv2d(pool1, W_conv2) + b_conv2)
# pool2
pool2 = tf.nn.avg_pool(
    conv2, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME', name='pool2')

# conv3
W_conv3 = weight_variable([3, 3, 32, 64], 0.01)
b_conv3 = bias_variable([64])
conv3 = tf.nn.relu(conv2d(pool2, W_conv3) + b_conv3)
# pool3
pool3 = tf.nn.avg_pool(
    conv3, ksize=[1, 3, 3, 1], strides=[1, 2, 2, 1], padding='SAME', name='pool3')


# softmax
pool3_flat = tf.reshape(pool3, [-1, 4 * 4 * 64])
W_out = weight_variable([4 * 4 * 64, 10], 0.1)
b_out = bias_variable([10])
pred = tf.matmul(pool3_flat, W_out) + b_out
# pred = tf.maximum(tf.nn.softmax(tf.matmul(pool3_flat, W_out) + b_out), 1e-30)


# cost function
# cost = -tf.reduce_sum(y_ * tf.log(y_conv))
cost = tf.reduce_mean(
    tf.nn.softmax_cross_entropy_with_logits(labels=y_, logits=pred))

# Adam optimizer
train_step = tf.train.AdamOptimizer(1e-4).minimize(cost)
# train_step = tf.train.MomentumOptimizer(learning_rate = 1e-4, momentum = 0.9).minimize(cost)

# count correct prediction
correct_prediction = tf.equal(tf.argmax(pred, 1), tf.argmax(y_, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"))

# save model
saver = tf.train.Saver()

# get cifar-10 dataset
cifar10_data_set = extract_cifar10.Cifar10DataSet('../dataset/')
test_images, test_labels = cifar10_data_set.test_data()

# define session
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    if isTrain:
        start_time = time.time()
        for i in xrange(500000):
            batch_xs, batch_ys = cifar10_data_set.next_train_batch(batch_size)
            if i % 1000 == 0:
                train_accuracy = accuracy.eval(
                    feed_dict={x: batch_xs, y_: batch_ys})
                print "step %d, training accuracy %g" % (i, train_accuracy)
                end_time = time.time()
                print 'time: ', (end_time - start_time)
                start_time = end_time

            if (i + 1) % 10000 == 0:
                avg = 0
                for j in xrange(20):
                    avg += accuracy.eval(
                        feed_dict={x: test_images[j * 50:j * 50 + 50], y_: test_labels[j * 50:j * 50 + 50]})
                avg /= 20
                print "\ntest accuracy %g\n" % avg

            train_step.run(feed_dict={x: batch_xs, y_: batch_ys})

        if not tf.gfile.Exists('output/model'):
            tf.gfile.MakeDirs('output/model')
        save_path = saver.save(sess, "output/model/model.ckpt")
        print "Model saved in file: ", save_path

        if not tf.gfile.Exists('output/weights'):
            tf.gfile.MakeDirs('output/weights')
# 		conv1_weights = sess.run(W_conv1)
# 		conv2_weights = sess.run(W_conv2)
# 		ip1_weights = sess.run(W_fc1)
# 		ip2_weights = sess.run(W_fc2)
# 		sio.savemat('output/weights/lenet_avg_pooling.mat', {'conv1_weights':conv1_weights,
#                                                             'conv2_weights':conv2_weights,
#                                                             'ip1_weights':ip1_weights,
#                                                             'ip2_weights':ip2_weights})

    else:
        saver.restore(sess, "output/model/model.ckpt")

    avg = 0
    for i in xrange(200):
        avg += accuracy.eval(
            feed_dict={x: test_images[i * 50:i * 50 + 50], y_: test_labels[i * 50:i * 50 + 50]})
    avg /= 200
    print "test accuracy %g" % avg
