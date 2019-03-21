# dig-text-similarity-search

## Overview
#### Text Search without Keywords:
This is a search engine for ranking news articles from LexisNexis 
by using sentence vector similarity rather than key word frequency. 


#### Basic Recipe:
1) Prepare text corpus as sentences with unique integer ids
2) Vectorize sentences with Google's [Universal Sentence Encoder](https://tfhub.dev/google/universal-sentence-encoder-large/3)
3) Put vectors into a searchable [Faiss index](https://github.com/facebookresearch/faiss)
4) Find the vectorized query's nearest neighbors


## Virtual Environment
#### Initialize:
```bash
conda env create .
source activate dig_text_similarity
ipython kernel install --user --name=dig_text_similarity
```

#### Deactivate:
```bash
source deactivate
```


## Usage
Vectorized similarity search does not rely on word frequency to find relevant results. 
Instead, dig-text-similarity-search will find a query's nearest neighbors within a corpus. 
In other words, it will return results that are similar to the query in terms of 
subject matter and structure. 

Empirically, we have found the large Universal Sentence Encoder 
[(a Deep Transformer Network)](https://tfhub.dev/google/universal-sentence-encoder-large/3) 
to give more interesting search results than the small Universal Sentence Encoder 
[(a Deep Averaging Network)](https://tfhub.dev/google/universal-sentence-encoder/2). 
The Transformer seems to be better at capturing the intent behind a sentence, 
whereas similar sentences within the DAN embedding space are less sensitive to nuance.

Note: The large USE is much more computationally expensive (preprocessing requires a GPU).

#### Arguments:

Arguments necessary to run every script in `py_scripts/preprocessing` and `py_scripts/service` can be 
viewed by running `python *.py -h`. 

Ex: 
```
python py_scripts/service/similarity_server.py -h
```

Returns: 
```
usage: similarity_server.py [-h] [-c CENTROIDS] [-l] [-d] index_dir_path

Deploy multiple faiss index shards as a RESTful API.

positional arguments:
  index_dir_path        Path to index shards.

optional arguments:
  -h, --help            show this help message and exit
  -c CENTROIDS, --centroids CENTROIDS
                        Number of centroids to visit during search. (Speed vs.
                        Accuracy trade-off)
  -l, --large           Toggle large Universal Sentence Encoder (Transformer).
                        Note: Encoder and Faiss embedding spaces must match!
  -d, --debug           Increases verbosity of Flask app.
```

#### To get started:
Dig-text-similarity-search is designed for very large text corpora (> 1 billion sentence vectors). 
Faiss indexes that are searchable on-disk are used to achieve this level of scalability. 

Build a small example index from the file `data/example/sample_news_2018-05-11.jl` by running:
```bash
#   Arg1: n news.jl files to index
#   Arg2: path/to/dir/ containing news.jl files (will select most recent date)
#   Arg3: path/to/save/ on-disk searchable news.index & news.ivfdata

./vectorize_n_small_shards.sh 1 data/example/ data/tmp_idx_files/
```

###### Note: Multi-Batch Vectorization usually uses larger batches of 65,536 sentences (i.e. 16,384 was chosen for illustrative purposes). 

After successfully indexing a `news.jl` file, its path will be recorded in `progress.txt`.

##### Every faiss shard should contain absolute partitions of the sentences within the corpus. Shards with conflicting `faiss_ids` may give incorrect results. 

#### Query vectorization with docker:
Before running the similarity server, encapsulate the Universal Sentence Encoder in a suitable 
form for running in a docker container with:

```bash
./prep_small_USE.sh
```

Then run the container locally through port `8501` for online query vectorization with: 

```bash
./run_small_USE.sh
```

Note: Although it is possible to do so, it is not recommended to use 
the dockerized model for preprocessing.

#### Configuration:
Configuration instructions for the similarity server can be found in `py_scripys/configs/config.py`

#### Similarity Service:
Run the server with:
```bash
python py_scripts/service/similarity_server.py data/tmp_idx_files/ -c 32
```

The index handler will load every shard in the `data/tmp_idx_files/` directory. The `-c` option specifies the number of 
data clusters to visit at query time and serves as the search Speed vs. Accuracy trade-off. Generally `-c 32` is 
appropriate for testing while in practice a service with numerous large indexes should use `-c 6`.

###### Note: There are 16384 neighborhoods in the pre-trained base index for the small USE embedding space (DAN), while the pre-trained base for the large USE (Transformer) has 4096 centroids (admittedly counterintuitive).

Test the server with: 
```bash
python py_scripts/service/call_similarity_service.py \
-q "What will be the short-term interest rate of Tesla stock in 2019?"
```

The similarity server returns integer vector ids and their difference scores (L2) relative to the query vector. 
##### It does not return text.
