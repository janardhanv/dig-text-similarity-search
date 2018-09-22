# dig-text-similarity-search


## Virtual Environment
#### Initialize:
```
conda env create .
source activate dig_text_similarity
ipython kernel install --user --name=dig_text_similarity
```

#### Run Unit Tests
Ensure hbase is running (see below: Run hbase docker)
```
python -W ignore -m unittest discover
```

#### Deactivate:
```
source deactivate
```


## Storage Adapter
Module for linking faiss_ids to content. 

(HBase has been depreciated)


## Installing TensorFlow from Source (for CPU)
TF Docs: https://www.tensorflow.org/install/install_sources <br />

#### Setup:
```
bazel version
brew upgrade bazel
```

#### Clone TensorFlow:
```
git clone https://github.com/tensorflow/tensorflow 
cd tensorflow
git checkout r1.9
```

#### Configure for CPU:
Ensure dig_text_similarity env is active.
```
./configure
```
Add XLA support. Set everything else to default.
```
Please specify the location of python. [Default is /anaconda3/envs/dig_text_similarity/bin/python]: 
...
Do you wish to build TensorFlow with XLA JIT support? [y/N]: y 
...
```

#### Build:
Note gcc version:
```
gcc -v
```
* If gcc 4: 
    ```
    bazel build --config=mkl --config=opt //tensorflow/tools/pip_package:build_pip_package
    ```
* If gcc 5 or later:
    ```
    bazel build --cxxopt="-D_GLIBCXX_USE_CXX11_ABI=0" --config=mkl --config=opt //tensorflow/tools/pip_package:build_pip_package
    ```
This will take a long time...

#### Create Package and Install:
```
bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg
pip install /tmp/tensorflow_pkg/tensorflow-*.whl
```
